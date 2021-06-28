import random

from hashlib import sha256

from django.db import models
from django.conf import settings
from django.utils.timezone import datetime, localtime, timedelta, utc
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


def distribute_all_safe():
    """Calculate UBP global amount and personal shares and safely
    distribute deposits. The function is *safe* because it has no effect
    if called more than once within the same (weekly) time epoch.
    """

    time = localtime()

    if Goal.objects.filter(created__gte=to_step_start(time)).exists():
        return

    goal, actual = get_distribution_amount(time)
    shares = get_distribution_shares(time)

    for person in shares:
        person.distributor.distribute_safe(
            time,
            round(actual * shares[person]),
        )

    Goal.objects.create(amount=goal, created=time)


def get_distribution_amount(time):
    """Using historical user data and a PID controller, calculate the
    optimal global UBP amount for the current week. The error is the
    deviation of effective weekly donations from the specified goal
    and the control signal is the weekly UBP amount. """

    goal = sum(
        x.amount for x in Grant.objects.filter(start__lte=time.date())
        if not x.duration
        or x.start + timedelta(days=7) * x.duration > time.date())
    error = [x[1] - x[0] for x in get_control_history(time)]

    # Let settle for first three weeks
    if len(error) < 3:
        return goal, goal

    # PID controller
    control = settings.DISTRIBUTION_CONTROLLER_KP * sum([
        error[-1],
        (1 / settings.DISTRIBUTION_CONTROLLER_TI) * sum(error),
        settings.DISTRIBUTION_CONTROLLER_TD * (error[-1] - error[-2]),
    ])

    # Impose max/min thresholds
    if control < -0.5 * goal:
        control = -0.5 * goal
    elif control > 0.5 * goal:
        control = 0.5 * goal

    return goal, goal - control


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
        [
            x.amount,
            sum([
                sum(  # sum of all donations
                    x.amount for x in ibis.models.Donation.objects.filter(
                        created__gte=to_step_start(x.created),
                        created__lt=to_step_start(x.created, offset=1))),
                -sum(  # sum of rewards
                    x.amount for x in ibis.models.Reward.objects.filter(
                        created__gte=to_step_start(x.created),
                        created__lt=to_step_start(x.created, offset=1))),
                -sum(  # sum of non-UBP deposits
                    x.amount for x in ibis.models.Deposit.objects.exclude(
                        category=ibis.models.ExchangeCategory.objects.get(
                            title=settings.IBIS_CATEGORY_UBP)).filter(
                                created__gte=to_step_start(x.created),
                                created__lt=to_step_start(x.created, offset=1))
                    if ibis.models.Person.objects.filter(
                        id=x.user.id).exists()),
            ]),
        ] for x in goals
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

    # will be 0, -1, or 1 hours off of the midnight, depending on tz
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


class Grant(TimeStampedModel):
    name = models.TextField()
    amount = models.PositiveIntegerField()
    start = models.DateField()
    duration = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return '{} ${:.2f} x {}'.format(
            self.name,
            self.amount / 100,
            self.duration if self.duration <= 0 else 'Indefinite',
        )


class Goal(TimeStampedModel):
    amount = models.PositiveIntegerField()


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
            _, total = get_distribution_amount(time)
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
