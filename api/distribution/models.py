import logging
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


def get_distribution_shares(time):
    """Calculate the relative UBP share for each active person based on the
    recency of their last activity (registration or donation).
    """

    step = to_step_start(time)

    # calculate raw relative shares
    raw = {}
    for x in ibis.models.Person.objects.exclude(is_active=False).exclude(
            distributor__eligible=False).exclude(date_joined__gte=step):
        activity = x.donation_set.filter(
            created__lt=step).order_by('created').last()
        last = to_step_start(
            localtime(activity.created)
            if activity else to_step_start(x.date_joined, offset=-1))
        weeks = (step.date() - last.date()).days / len(DAYS)
        raw[x] = int(2**(settings.DISTRIBUTION_HORIZON - weeks))

    # prune and normalize
    total = sum(raw.values())
    return {x: raw[x] / total for x in raw if raw[x]} if total else {}


def get_distribution_initial(time):
    total = get_distribution_amount(time)
    shares = get_distribution_shares(time)
    new = [
        x for x in ibis.models.Person.objects.filter(
            date_joined__gte=to_step_start(time))
        if x.person.deposit_set.filter(
            category=ibis.models.ExchangeCategory.objects.get(
                title=settings.IBIS_CATEGORY_UBP)).exists()
    ]

    return max(
        1,
        round((total * max(shares.values()) * (1 + len(shares)) /
               (1 + len(shares) + len(new))) if shares else (total /
                                                             (1 + len(new)))),
    )


def refresh_accounting():
    items = sorted(
        list(ibis.models.Grant.objects.all()) +
        list(ibis.models.Donation.objects.all()),
        key=lambda x: x.created,
    )

    accounting = set()
    grants = {}
    donations = {}

    for item in items:
        if type(item) == ibis.models.Grant:
            grants[item] = {'left': item.amount, 'score': (0, item.created)}
        else:
            donations[item] = {'left': item.amount, 'score': item.created}

        while donations and grants:
            donation = min(donations, key=lambda x: donations[x]['score'])
            for grant in grants:
                grants[grant]['score'] = (
                    -round((to_step_start(donation.created) -
                            to_step_start(grant.created, offset=1)).days / 7) +
                    grant.duration *
                    (grant.amount - grants[grant]['left']) / grant.amount,
                    grant.created,
                )

            grant = min(grants, key=lambda x: grants[x]['score'])
            if grants[grant]['left'] > donations[donation]['left']:
                grants[grant]['left'] -= donations[donation]['left']
                accounting.add((grant, donation, donations[donation]['left']))
                del donations[donation]
            elif grants[grant]['left'] < donations[donation]['left']:
                donations[donation]['left'] -= grants[grant]['left']
                accounting.add((grant, donation, grants[grant]['left']))
                del grants[grant]
            else:
                accounting.add((grant, donation, grants[grant]['left']))
                del donations[donation]
                del grants[grant]

    accounted = set((
        x.grant,
        x.donation,
        x.amount,
    ) for x in ibis.models.GrantDonation.objects.all())

    for g, d, _ in accounted - accounting:
        ibis.models.GrantDonation.objects.filter(
            grant=g,
            donation=d,
        ).delete()

    for g, d, a in accounting - accounted:
        ibis.models.GrantDonation.objects.create(
            grant=g,
            donation=d,
            amount=a,
        )


def to_step_start(time, offset=0):
    """Calculate the exact time (midnight) of the previous timestep as
    defined by the project settings. The optional offset parameter
    increments or decrements the provided number of weeks
    """

    if not isinstance(time, datetime):
        time = datetime.combine(
            time,
            datetime.min.time(),
            tzinfo=localtime().tzinfo,
        )

    time = localtime(time)

    # will be 0, -1, or 1 hours off of midnight, depending on tz
    raw = localtime(
        datetime.combine(
            time.date() - timedelta(days=(
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


class Goal(TimeStampedModel):
    processed = models.BooleanField(default=False)

    @staticmethod
    def amount_static(created, offset=0):
        return sum(x.amount / x.duration
                   for x in ibis.models.Grant.objects.filter(
                       created__lt=to_step_start(created, offset=offset))
                   if to_step_start(x.created, offset=x.duration) >=
                   to_step_start(created, offset=offset))

    def amount(self):
        return Goal.amount_static(self.created)


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
        return '@' + str(self.person.username)

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
        self.distribute_safe(
            time,
            amount=get_distribution_initial(time),
        )
