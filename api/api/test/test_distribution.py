import os
import json
import random
import ibis.models
import distribution.models
import distribution.signals

from django.db.models import Sum
from django.core import management
from django.utils.timezone import localtime, timedelta, utc
from django.conf import settings
from freezegun import freeze_time
from api.test.base import BaseTestCase, TEST_TIME
from graphql_relay.node.node import to_global_id

DIR = os.path.dirname(os.path.realpath(__file__))

TS_WEEKS = 9
SS_WEEKS = 15

UBP_CATEGORY = ibis.models.DepositCategory.objects.get(
    title=settings.IBIS_CATEGORY_UBP)

EPSILON = 1.0

with open(os.path.join(DIR, '../../../config.json')) as fd:
    CONF = json.load(fd)


class DistributionTestCase(BaseTestCase):
    def setUp(self, *args, **kwargs):
        settings.DISTRIBUTION_DAY = 'Friday'
        settings.DISTRIBUTION_GOAL = 100000
        self._max_transfer_old = settings.MAX_TRANSFER
        settings.MAX_TRANSFER = 1e20
        if hasattr(settings, 'DISTRIBUTION_INITIAL'):
            del settings.DISTRIBUTION_INITIAL

        super().setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        settings.MAX_TRANSFER = self._max_transfer_old
        super().tearDown(*args, **kwargs)

    def _donate(self, user, target, amount):
        self._client.force_login(user)
        assert 'errors' not in json.loads(
            self.query(
                self.gql['DonationCreate'],
                op_name='DonationCreate',
                variables={
                    'user': to_global_id('IbisUserNode', user.id),
                    'target': to_global_id('NonprofitNode', target.id),
                    'amount': amount,
                    'description': 'This is a donation',
                },
            ).content)

    def _transact(self, user, target, amount):
        self._client.force_login(user)
        assert 'errors' not in json.loads(
            self.query(
                self.gql['TransactionCreate'],
                op_name='TransactionCreate',
                variables={
                    'user': to_global_id('IbisUserNode', user.id),
                    'target': to_global_id('PersonNode', target.id),
                    'amount': amount,
                    'description': 'This is a transaction',
                },
            ).content)

    def _deposit(self, user, amount):
        ibis.models.Deposit.objects.create(
            user=user,
            amount=amount,
            payment_id=str(random.random()),
            category=ibis.models.DepositCategory.objects.exclude(
                id=UBP_CATEGORY).first(),
        )

    def _fast_forward_cron(self, frozen_datetime, number, **kwargs):
        for _ in range(number):
            frozen_datetime.tick(delta=timedelta(**kwargs))
            management.call_command('distribute')

    def test_times(self):
        with freeze_time(TEST_TIME.astimezone(utc).date()) as frozen_datetime:
            times = [
                distribution.models.to_step_start(localtime(), offset=i)
                for i in range(-100, 100)
            ]
            for i, x in enumerate(times[:-1]):
                assert x.weekday() == 4  # Friday
                assert x < times[i + 1]
                assert x.date() < times[i + 1].date()
            assert distribution.models.to_step_start(
                localtime()) <= localtime()
            assert distribution.models.to_step_start(
                localtime(), offset=1) > localtime()

    def test_initial(self):
        settings.DISTRIBUTION_INITIAL = 1000
        person1 = ibis.models.Person.objects.create(
            username=str(random.random())[:15],
            password='password',
            first_name='Person',
            last_name='McPersonFace_Initial_1',
        )

        del settings.DISTRIBUTION_INITIAL

        person2 = ibis.models.Person.objects.create(
            username=str(random.random())[:15],
            password='password',
            first_name='Person',
            last_name='McPersonFace_Initial_2',
        )

        assert person1.deposit_set.count() == 1
        assert person1.balance() == 1000
        assert person2.deposit_set.count() == 1
        assert person2.balance() != 1000

    def test_distribution(self):
        def _create_person(activity):
            activity[ibis.models.Person.objects.create(
                username=str(random.random())[:15],
                password='password',
                first_name='Person',
                last_name='McPersonFace{}'.format(
                    ibis.models.Person.objects.count()),
                email='person@example.com',
            )] = 1

        def _check_transient(activity):
            step = distribution.models.to_step_start(localtime())
            payouts = {
                x: ibis.models.Deposit.objects.filter(
                    user=x,
                    category=UBP_CATEGORY,
                    created__gte=step,
                ).aggregate(Sum('amount'))['amount__sum']
                for x in activity
            }

            by_tier = [[
                payouts[y] for y in payouts
                if activity[y] == x and y.date_joined < step
            ] for x in range(settings.DISTRIBUTION_HORIZON)]

            for i, x in enumerate(by_tier):
                if x:
                    # make sure that all users in same tier gets same payout
                    assert all(y == x[0] for y in x)

                    # check exponential backoff
                    if by_tier[0]:
                        assert abs(x[0] * 2**i - by_tier[0][0]) < 1e5

            # check that there is no payout of activity exceeds horizon
            assert not any(payouts[x] for x in activity
                           if activity[x] >= settings.DISTRIBUTION_HORIZON)

            # check that new users get paid something, but less than active
            for x in activity:
                if x.date_joined >= step:
                    assert payouts[x]
                    if by_tier[0]:
                        assert payouts[x] < by_tier[0][0]

        def _tick_transient(activity, users):
            for x in activity:
                if x in users:
                    if random.random() < 0.5:
                        ibis.models.Deposit.objects.create(
                            user=x,
                            amount=10000,
                            category=ibis.models.DepositCategory.objects.
                            exclude(id=UBP_CATEGORY.id).first(),
                            payment_id=str(random.random()),
                        )

                    # randomly give away roughly half of balance
                    amounts = [
                        random.random() for _ in range(random.randint(1, 4))
                    ]
                    amounts = [
                        int(a / sum(amounts) * x.balance() * random.random())
                        for a in amounts
                    ]
                    amounts = [x if x else 1 for x in amounts]
                    for y in amounts:
                        if random.random() < 0.5:
                            self._donate(
                                user=x,
                                target=ibis.models.Nonprofit.objects.order_by(
                                    '?').first(),
                                amount=y,
                            )
                        else:
                            self._transact(
                                user=x,
                                target=ibis.models.Person.objects.order_by(
                                    '?').first(),
                                amount=y,
                            )
                    activity[x] = 0
                else:
                    activity[x] += 1

            for x in users:
                if ibis.models.Nonprofit.objects.filter(
                        id=x.id).exists() and x.balance() > 1000:
                    ibis.models.Withdrawal.objects.create(
                        user=x,
                        amount=x.balance() - 1000,
                    )

        def _tick_steady_state(activity):
            # users who are already active send money and are active to eachother
            for x in activity:
                if activity[x] == 0:
                    amounts = [
                        random.random() for _ in range(random.randint(1, 3))
                    ]
                    amounts = [a / sum(amounts) * x.balance() for a in amounts]
                    for y in amounts:
                        self._donate(
                            user=x,
                            target=ibis.models.Nonprofit.objects.order_by(
                                '?').first(),
                            amount=y,
                        )
                    activity[x] = 0
                else:
                    activity[x] += 1

        def _check_epoch():
            steps = [
                distribution.models.to_step_start(x.created)
                for x in distribution.models.Goal.objects.all()
            ][:-1]

            goals = [x.amount for x in distribution.models.Goal.objects.all()]

            # make sure goal events are properly spaced and contiguous
            assert all((steps[i + 1] - steps[i]).days == 7
                       for i in range(len(steps) - 1))

            # list of (control amount, adjusted donation amount) for each step
            def _none_zero(x):
                return x if x else 0

            regular_ubp = [
                sum(
                    x.amount for x in ibis.models.Deposit.objects.filter(
                        category=UBP_CATEGORY,
                        created__gte=x,
                        created__lt=x + timedelta(days=7),
                    ) if x != x.user.deposit_set.first()) for x in steps
            ]

            adjusted = [
                sum([
                    _none_zero(
                        ibis.models.Donation.objects.filter(
                            created__gte=x,
                            created__lt=x + timedelta(days=7),
                        ).aggregate(Sum('amount'))['amount__sum']),
                    -_none_zero(
                        ibis.models.Donation.objects.filter(
                            user__nonprofit__isnull=False,
                            created__gte=x,
                            created__lt=x + timedelta(days=7),
                        ).aggregate(Sum('amount'))['amount__sum']),
                    -_none_zero(
                        ibis.models.Transaction.objects.filter(
                            user__nonprofit__isnull=False,
                            created__gte=x,
                            created__lt=x + timedelta(days=7),
                        ).aggregate(Sum('amount'))['amount__sum']),
                    -_none_zero(
                        ibis.models.Deposit.objects.exclude(
                            category=UBP_CATEGORY).filter(
                                created__gte=x,
                                created__lt=x + timedelta(days=7),
                            ).aggregate(Sum('amount'))['amount__sum']),
                ]) for x in steps
            ]

            assert all(
                x[0] == goals[i] and x[1] == adjusted[i] for i, x in enumerate(
                    distribution.models.get_control_history(localtime())[:-1]))

            # make sure that the control signal never exceeds bounds
            for i in range(len(steps)):
                assert regular_ubp[i] == 0 or (
                    regular_ubp[i] >= goals[i] * 0.4
                    and regular_ubp[i] <= goals[i] * 1.6)

            # ensure monotonic convergence for latter half of steady state
            abs_error = [
                abs(goals[0] - adjusted[-1]) for i in range(len(steps))
            ]
            assert all(abs_error[i] <= abs_error[i - 1]
                       for i in range(int(-SS_WEEKS / 2),
                                      len(abs_error) - 1))

            # make sure the difference is within a reasonable amount
            assert abs(
                sum(goals[i] - adjusted[i] for i in range(len(steps)))
            ) < distribution.models.Goal.objects.last().amount * EPSILON

        with freeze_time(TEST_TIME.astimezone(utc).date()) as frozen_datetime:

            sink = ibis.models.Nonprofit.objects.last()

            # number of weeks since last active (last week == 0)
            for x in ibis.models.IbisUser.objects.exclude(id=sink.id):
                ibis.models.Deposit.objects.create(
                    user=x,
                    amount=2000,
                    category=UBP_CATEGORY,
                    payment_id=str(random.random()),
                )
                self._donate(
                    user=x,
                    target=sink,
                    amount=x.balance() - 1000,
                )

            ibis.models.Withdrawal.objects.create(
                user=sink,
                amount=sink.balance() - 1000,
            )
            activity = {x: 0 for x in ibis.models.Person.objects.all()}

            # make sure everything has settled
            for i in range(settings.DISTRIBUTION_HORIZON + 1):
                frozen_datetime.tick(delta=timedelta(days=(7 * 5)))
                activity = {x: activity[x] + 1 for x in activity}

            # trigger first (failed) attempt at payment
            self._fast_forward_cron(frozen_datetime, 2, seconds=5)

            # Epoch 1: random
            for _ in range(TS_WEEKS):
                _tick_transient(
                    activity,
                    users=random.sample(
                        list(activity) + list(ibis.models.Nonprofit.objects.
                                              all()[:int(len(activity) / 2)]),
                        int(len(activity) / 2),
                    ),
                )
                if random.random() < 0.25:
                    _create_person(activity)
                self._fast_forward_cron(frozen_datetime, 7, days=1)
                _check_transient(activity)

            for _ in range(SS_WEEKS):
                _tick_steady_state(activity)
                self._fast_forward_cron(frozen_datetime, 7, days=1)

            _check_epoch()

            # Epoch 2: trough
            remaining = list(activity)
            for _ in range(TS_WEEKS):
                _tick_transient(activity, remaining)
                if len(remaining) >= 4:
                    remaining = remaining[:int(len(remaining) / 2)]
                self._fast_forward_cron(frozen_datetime, 7, days=1)
                _check_transient(activity)

            for _ in range(SS_WEEKS):
                _tick_steady_state(activity)
                self._fast_forward_cron(frozen_datetime, 7, days=1)

            _check_epoch()

            # Epoch 3: surge
            for _ in range(TS_WEEKS):
                # add random number of users every week
                _tick_transient(
                    activity,
                    users=random.sample(
                        list(activity) + list(ibis.models.Nonprofit.objects.
                                              all()[:int(len(activity) / 4)]),
                        len(activity),
                    ),
                )
                for _ in range(random.randint(1, 4)):
                    _create_person(activity)
                self._fast_forward_cron(frozen_datetime, 7, days=1)
                _check_transient(activity)

            for _ in range(SS_WEEKS):
                _tick_steady_state(activity)
                self._fast_forward_cron(frozen_datetime, 7, days=1)

            _check_epoch()

            # Epoch 4: moon
            settings.DISTRIBUTION_GOAL *= 4
            for _ in range(TS_WEEKS):
                _tick_transient(
                    activity,
                    users=random.sample(
                        list(activity) + list(ibis.models.Nonprofit.objects.
                                              all()[:int(len(activity) / 4)]),
                        len(activity),
                    ),
                )
                self._fast_forward_cron(frozen_datetime, 7, days=1)
                _check_transient(activity)

            for _ in range(SS_WEEKS):
                _tick_steady_state(activity)
                self._fast_forward_cron(frozen_datetime, 7, days=1)

            _check_epoch()
