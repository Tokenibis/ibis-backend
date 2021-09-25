import logging
import random

from collections import defaultdict
from hashlib import sha256

from django.db import models
from django.conf import settings
from django.utils.timezone import datetime, localtime, timedelta, utc
from datetime import date
from model_utils.models import TimeStampedModel
from annoying.fields import AutoOneToOneField

import ibis.models

DAYS = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
)

logger = logging.getLogger(__name__)


def distribute_all_safe():
    """Calculate UBP global amount and personal shares and safely
    distribute deposits. The function is *safe* because it has no effect
    if called more than once within the same (weekly) time epoch.
    """

    time = localtime()

    if Goal.objects.filter(
            created__gte=to_step_start(time),
            processed=True,
    ).exists():
        return
    elif Goal.objects.filter(
            created__gte=to_step_start(time),
            processed=False,
    ).exists():
        goal = Goal.objects.get(created__gte=time, processed=False)
    else:
        goal = Goal.objects.create(created=time)

    actual = get_distribution_amount(time)
    shares = get_distribution_shares(time)

    for person in shares:
        person.distributor.distribute_safe(
            time,
            round(actual * shares[person]),
        )

    goal.processed = True
    goal.save()


def get_distribution_amount(time):
    """Using historical user data and a PID controller, calculate the
    optimal global UBP amount for the current week. The error is the
    deviation of effective weekly donations from the specified goal
    and the control signal is the weekly UBP amount. """

    try:
        goal_amount = Goal.objects.get(
            created__gte=to_step_start(time)).amount()
    except Goal.DoesNotExist:
        goal_amount = 0

    error = [x[1] - x[0] for x in get_control_history(time)]

    # Let settle for first three weeks
    if len(error) < 3:
        return goal_amount

    # PID controller
    control = settings.DISTRIBUTION_CONTROLLER_KP * sum([
        error[-1],
        (1 / settings.DISTRIBUTION_CONTROLLER_TI) * sum(error),
        settings.DISTRIBUTION_CONTROLLER_TD * (error[-1] - error[-2]),
    ])

    # Impose max/min thresholds
    if control < -0.5 * goal_amount:
        control = -0.5 * goal_amount
    elif control > 0.5 * goal_amount:
        control = 0.5 * goal_amount

    return goal_amount - control


def get_control_history(time):
    """Calculate the historical control (goal, adjusted donations) as a
    timeseries. The effective donation adjusts for user deposits. The
    control error can be calculated as the difference of each pair of
    data points.

    """

    goals = list(
        Goal.objects.filter(
            created__lt=to_step_start(time)).order_by('created'))

    return [
        (
            x.amount(),
            sum(  # sum of all donations
                x.amount for x in ibis.models.Donation.objects.filter(
                    created__gte=to_step_start(x.created),
                    created__lt=to_step_start(x.created, offset=1))),
        ) for x in goals
    ]


def get_distribution_shares(time, initial=[]):
    """Calculate the relative UBP share for each active person based on the
    recency of their last activity (registration or donation).
    """

    step = to_step_start(time)

    # calculate raw relative shares
    raw = {}
    for x in ibis.models.Person.objects.exclude(distributor__eligible=False):
        activity = x.donation_set.filter(
            created__lt=step).order_by('created').last()
        last = to_step_start(
            localtime(activity.created) if activity else to_step_start(
                x.date_joined, offset=-1))
        weeks = (step.date() - last.date()).days / len(DAYS)
        raw[x] = int(2**(settings.DISTRIBUTION_HORIZON - weeks))

    for x in initial:
        if x.distributor.eligible:
            raw[x] = 2**(settings.DISTRIBUTION_HORIZON - 1)

    # prune and normalize
    total = sum(raw.values())
    return {x: raw[x] / total for x in raw if raw[x]} if total else {}


def to_step_start(time, offset=0):
    """Calculate the exact time (midnight) of the previous timestep as
    defined by the project settings. The optional offset parameter
    increments or decrements the provided number of weeks
    """

    if isinstance(time, date):
        time = datetime.combine(
            time,
            datetime.min.time(),
            tzinfo=localtime().tzinfo,
        )

    # will be 0, -1, or 1 hours off of midnight, depending on tz
    raw = localtime(
        datetime.combine(
            time.date() - timedelta(
                days=(
                    (time.weekday() - DAYS.index(settings.DISTRIBUTION_DAY)) %
                    len(DAYS)) - offset * len(DAYS)),
            datetime.min.time(),
            tzinfo=time.tzinfo,
        ).astimezone(utc))

    # just round to the correct time
    return datetime.combine(
        (raw + timedelta(hours=12)).date(),
        datetime.min.time(),
        tzinfo=raw.tzinfo,
    )


class Investment(TimeStampedModel):
    name = models.TextField()
    amount = models.PositiveIntegerField()
    start = models.DateField()
    end = models.DateField()
    description = models.TextField(blank=True, null=True)
    deposit = models.ForeignKey(
        ibis.models.Deposit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    funded = models.ManyToManyField(
        ibis.models.Donation,
        related_name='funded_by',
        blank=True,
    )

    @property
    def info_str(self):
        amounts = sum(x.amount for x in self.funded.all())

        return '\n'.join('{}: {}'.format(x, y) for x, y in [
            ('Total Investment', '${:.2f}'.format(self.amount / 100)),
            ('Donations Funded', self.funded.count()),
            ('Spending Timeline', '{} to {}'.format(self.start, self.end)),
            ('Percent Spent',
             '{}%'.format(min(100, round(100 * amounts / self.amount)))),
        ])

    @staticmethod
    def account_investments():
        def _diff(t1, t2):
            return round((to_step_start(t1) - to_step_start(t2)).days / 7)

        result = defaultdict(lambda: set())

        investments = list(Investment.objects.order_by('start'))

        # grid where rows are investments and columns are weeks
        grid = [[
            0 for x in range(
                _diff(
                    Investment.objects.order_by('end').last().end,
                    investments[0].start,
                ) + 1)
        ] for _ in investments]

        # fill grid with money amounts from investments
        for i, x in enumerate(investments):
            chunk = int(x.amount / (_diff(x.end, x.start) + 1))
            for j in range(
                    _diff(x.start, investments[0].start),
                    _diff(x.end, investments[0].start),
            ):
                grid[i][j] = chunk
            grid[i][_diff(
                x.end,
                investments[0].start,
            )] = x.amount - chunk * _diff(x.end, x.start)

        # account grid with money from donations
        i, j = 0, 0
        try:
            for x in ibis.models.Donation.objects.order_by('created'):
                remainder, offset, anchor = x.amount, 0, i

                while remainder > 0:
                    if grid[i][j + offset]:
                        result[investments[i]].add(x)
                        if remainder > grid[i][j + offset]:
                            remainder -= grid[i][j + offset]
                            grid[i][j + offset] = 0
                        else:
                            grid[i][j + offset] -= remainder
                            remainder = 0
                    else:
                        if j + offset + 1 < len(
                                grid[0]) and grid[i][j + offset + 1] > 0:
                            # still have space on the current investment
                            offset += 1
                        elif (i + 1) % len(grid) != anchor:
                            # still have more investments in the current week
                            offset, i = (0, (i + 1) % len(grid))
                        elif j + 1 < len(grid[0]):
                            # still have more weeks to increment to
                            i, j, offset = anchor, j + 1, 0
                        else:
                            # uh-oh, we're probably broke
                            raise ValueError('More donations than investments')

                i = (i + 1) % len(grid)
        except ValueError as e:
            logger.warning(e)

        for investment, donations in result.items():
            if not set(investment.funded.all()) == donations:
                investment.funded.clear()
                investment.funded.add(*donations)

    def __str__(self):
        return '{} ${:.2f} {} - {}'.format(
            self.name,
            self.amount / 100,
            self.start,
            self.end,
        )


class Goal(TimeStampedModel):
    processed = models.BooleanField(default=False)

    def amount(self):
        return sum(x.amount / (
            (to_step_start(x.end, offset=1) - to_step_start(x.start)).days / 7)
                   for x in Investment.objects.filter(
                       end__gte=to_step_start(self.created),
                       start__lt=to_step_start(self.created, offset=1)))


class Distributor(models.Model):
    person = AutoOneToOneField(
        ibis.models.Person,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    eligible = models.BooleanField(default=True)

    def distribute_safe(self, time, amount):
        """Distribute a UBP payment of the specified amount to the person. The
        function is *safe* because it has no effect if called more than once
        within the same (weekly) time epoch.
        """
        if self.eligible and not self.person.deposit_set.filter(
                created__gte=to_step_start(time),
                category=ibis.models.ExchangeCategory.objects.get(
                    title=settings.IBIS_CATEGORY_UBP),
        ).exists():
            ibis.models.Deposit.objects.create(
                user=self.person,
                amount=amount,
                description='ubp:{}'.format(
                    sha256(str(random.random()).encode('utf-8')).hexdigest()),
                category=ibis.models.ExchangeCategory.objects.get(
                    title=settings.IBIS_CATEGORY_UBP),
                created=time,
            )

    def __str__(self):
        return str(self.person)

    def distribute_initial_safe(self):
        """Distribute the initial UBP payment to a the new person. The amount
        is calculated as the maximum possible payout from the previous
        week adjusted to gradually decrease if too many users join in
        the same week. The function is *safe* because it has no effect
        if called more than once in the lifetime of a user.
        """

        if self.person.deposit_set.filter(
                category=ibis.models.ExchangeCategory.objects.get(
                    title=settings.IBIS_CATEGORY_UBP)).exists():
            return

        time = localtime()

        if hasattr(settings, 'DISTRIBUTION_INITIAL'):
            self.distribute_safe(
                time,
                amount=settings.DISTRIBUTION_INITIAL,
            )
        else:
            total = get_distribution_amount(time)
            shares = get_distribution_shares(time, initial=[self.person])
            population_discount = len(shares) / (
                ibis.models.Deposit.objects.filter(
                    created__gte=to_step_start(time),
                    category=ibis.models.ExchangeCategory.objects.get(
                        title=settings.IBIS_CATEGORY_UBP),
                ).count() + 1)

            self.distribute_safe(
                time,
                amount=total * shares[self.person] * population_discount,
            )
