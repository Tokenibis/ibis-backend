import os
import json
import random
import ibis.models
import distribution.models
import distribution.crons
import distribution.signals

from django.core import management
from django.utils.timezone import localtime, timedelta, utc, now
from django.conf import settings
from freezegun import freeze_time
from api.test.base import BaseTestCase, TEST_TIME

DIR = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(DIR, '../../../config.json')) as fd:
    CONF = json.load(fd)


class DistributionTestCase(BaseTestCase):
    def setUp(self, *args, **kwargs):
        distribution.crons.STATE['UPCOMING'] = localtime(now()).replace(
            year=2019,
            month=4,
            day=5,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        settings.DISTRIBUTION_DAY = 'Friday'
        settings.DISTRIBUTION_DEFAULT = CONF['ibis']['distribution']['default']
        settings.DISTRIBUTION_THROUGHPUT = CONF['ibis']['distribution'][
            'throughput']

        with freeze_time(TEST_TIME.astimezone(utc).date()):
            super().setUp(*args, **kwargs)

    def _do_transfer(self, user):
        if user.deposit_set.exists():
            deposit = user.deposit_set.first()
            deposit.amount += 1
            deposit.save()
        else:
            ibis.models.Deposit.objects.create(
                user=user,
                amount=1,
                payment_id=str(random.random()),
                category=ibis.models.DepositCategory.objects.first(),
            )

        if random.random() < 0.5:
            target = random.choice([
                x for x in ibis.models.Person.objects.all()
                if x.deposit_set.exists() and x.deposit_set.first().amount > 1
            ])
            ibis.models.Transaction.objects.create(
                user=user,
                target=target,
                amount=1,
                description='',
            )
            deposit = target.deposit_set.first()
            deposit.amount -= 1
            deposit.save()
        else:
            target = random.choice([
                x for x in ibis.models.Nonprofit.objects.all()
                if x.withdrawal_set.exists()
            ])
            ibis.models.Donation.objects.create(
                user=user,
                target=target,
                amount=1,
                description='',
            )
            withdrawal = target.withdrawal_set.first()
            withdrawal.amount += 1
            withdrawal.save()

    def _fast_forward_cron(self, frozen_datetime, number, **kwargs):
        for _ in range(number):
            frozen_datetime.tick(delta=timedelta(**kwargs))
            management.call_command(
                'runcrons',
                'distribution.crons.DistributionCron',
                '--force',
            )

    def test_times(self):
        def _test_get_times(test_time, **kwargs):
            day_start = localtime(TEST_TIME.astimezone(utc)).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            previous_expected = [
                day_start.replace(month=3, day=6),
                day_start.replace(month=3, day=13),
                day_start.replace(month=3, day=20),
                day_start.replace(month=3, day=27),
                day_start.replace(month=4, day=3),
            ]
            upcoming_expected = day_start.replace(month=4, day=10)

            times = distribution.models.Distributor._get_times(test_time)

            assert all(x[0] + timedelta(**kwargs) == x[1]
                       for x in zip(previous_expected, times[0]))
            assert times[1] == upcoming_expected + timedelta(**kwargs)

        # 2020-04-05
        _test_get_times(TEST_TIME.astimezone(utc), days=7 * 0)

        # just before next shift
        _test_get_times(
            localtime(TEST_TIME.astimezone(utc)).replace(
                day=9, hour=23, second=59, microsecond=999999).astimezone(utc),
            days=7 * 0)

        # during the next shift
        _test_get_times(
            localtime(TEST_TIME.astimezone(utc)).replace(
                day=10, hour=0, second=0, microsecond=0).astimezone(utc),
            days=7 * 1)

        # just before next shift way in the future and out of daylight savings
        _test_get_times(
            localtime(TEST_TIME.astimezone(utc)).replace(
                day=9, hour=23, second=59, microsecond=999999).astimezone(utc)
            + timedelta(days=7 * 10000, hours=1),
            days=7 * 10000,
            hours=1)

        # during the next shift way in the future and out of daylight savings
        _test_get_times(
            localtime(TEST_TIME.astimezone(utc)).replace(
                day=10, hour=0, second=0, microsecond=0).astimezone(utc) +
            timedelta(days=7 * 10000, hours=1),
            days=7 * (1 + 10000),
            hours=1)

    def test_distribution_none(self):

        total_balance = sum(
            x.balance() for x in ibis.models.IbisUser.objects.all())

        settings.DISTRIBUTION_THROUGHPUT = 10000
        settings.DISTRIBUTION_DEFAULT = 1000

        def _do_activity(frozen_datetime, transactions=True):
            for i in range(14):
                if transactions:
                    for i in range(5):
                        self._do_transfer(
                            random.choice(
                                list(ibis.models.IbisUser.objects.all())))
                self._fast_forward_cron(frozen_datetime, 2, hours=12)

        for x in ibis.models.Person.objects.all():
            y = x.distributor
            y.eligible = False
            y.save()

        with freeze_time(TEST_TIME.astimezone(utc).date()) as frozen_datetime:
            _do_activity(frozen_datetime)

        assert total_balance == sum(
            x.balance() for x in ibis.models.IbisUser.objects.all())

        settings.DISTRIBUTION_THROUGHPUT = 0
        settings.DISTRIBUTION_DEFAULT = 0

        for x in ibis.models.Person.objects.all():
            y = x.distributor
            y.eligible = True
            y.save()

        with freeze_time(TEST_TIME.astimezone(utc)) as frozen_datetime:
            ibis.models.Person.objects.create(username='distribution_none')
            _do_activity(frozen_datetime)

        assert total_balance == sum(
            x.balance() for x in ibis.models.IbisUser.objects.all())

        settings.DISTRIBUTION_THROUGHPUT = 10000
        settings.DISTRIBUTION_DEFAULT = 1000

        with freeze_time(TEST_TIME.astimezone(utc)) as frozen_datetime:
            _do_activity(frozen_datetime, transactions=False)

        assert total_balance == sum(
            x.balance() for x in ibis.models.IbisUser.objects.all())

    def test_distribution_positive(self):

        balances = {x: x.balance() for x in ibis.models.Person.objects.all()}

        transacting = random.sample(
            list(ibis.models.Person.objects.all()),
            round(len(balances) / 2),
        )

        active, inactive = transacting[:-1], transacting[-1:]

        for x in inactive:
            distributor = x.distributor
            distributor.eligible = False
            distributor.save()

        with freeze_time(TEST_TIME.astimezone(utc)) as frozen_datetime:
            for _ in range(2):
                # make sure everything has settled
                frozen_datetime.tick(delta=timedelta(days=(7 * 5)))

                # cold start
                for x in active + inactive:
                    self._do_transfer(x)
                self._fast_forward_cron(frozen_datetime, 1, days=1)
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # first distribution - verify bootstrap
                self._fast_forward_cron(frozen_datetime, 6, days=1)
                for x in [y for y in active if y != inactive]:
                    balances[x] += settings.DISTRIBUTION_DEFAULT
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # second distribution - verify throughout addition
                for x in active + inactive:
                    self._do_transfer(x)
                self._fast_forward_cron(frozen_datetime, 7, days=1)
                for x in [y for y in active if y != inactive]:
                    balances[x] += round(
                        settings.DISTRIBUTION_THROUGHPUT / (len(active)) * 0.4
                        + settings.DISTRIBUTION_DEFAULT * 0.6, )
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # third distribution - verify drop out
                active = active[:-2]
                for x in active:
                    self._do_transfer(x)
                self._fast_forward_cron(frozen_datetime, 24 * 7, hours=1)
                for x in [y for y in active if y != inactive]:
                    balances[x] += round(
                        settings.DISTRIBUTION_THROUGHPUT / (len(active)) * 0.4
                        + settings.DISTRIBUTION_THROUGHPUT / (len(active) + 2)
                        * 0.3 + settings.DISTRIBUTION_DEFAULT * 0.3, )
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # add 1st new person
                new_1 = ibis.models.Person.objects.create(
                    username=str(random.random()))
                amount = settings.DISTRIBUTION_THROUGHPUT / (
                    len(active)) * 0.4 + settings.DISTRIBUTION_THROUGHPUT / (
                        len(active) +
                        2) * 0.3 + settings.DISTRIBUTION_DEFAULT * 0.3
                balances[new_1] = round(
                    amount * settings.DISTRIBUTION_THROUGHPUT /
                    (settings.DISTRIBUTION_THROUGHPUT + amount))
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # add 2nd new person
                new_2 = ibis.models.Person.objects.create(
                    username=str(random.random()))
                amount = settings.DISTRIBUTION_THROUGHPUT / (
                    len(active)) * 0.4 + settings.DISTRIBUTION_THROUGHPUT / (
                        len(active) +
                        2) * 0.3 + settings.DISTRIBUTION_DEFAULT * 0.3
                balances[new_2] = round(
                    amount * settings.DISTRIBUTION_THROUGHPUT /
                    (settings.DISTRIBUTION_THROUGHPUT + amount * 2))
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # fourth distribution - verify adding one new person
                active = active + [new_1]
                for x in active + inactive:
                    self._do_transfer(x)
                self._fast_forward_cron(
                    frozen_datetime, 60 * 24 * 7, minutes=1)
                for x in [y for y in active if y != inactive]:
                    balances[x] += round(
                        settings.DISTRIBUTION_THROUGHPUT / (len(active)) * 0.4
                        + settings.DISTRIBUTION_THROUGHPUT / (len(active) - 1)
                        * 0.3 + settings.DISTRIBUTION_THROUGHPUT /
                        (len(active) + 1) * 0.2 +
                        settings.DISTRIBUTION_DEFAULT * 0.1, )
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # fifth distribution - downtime recovery
                for x in active + inactive:
                    self._do_transfer(x)
                frozen_datetime.tick(delta=timedelta(days=7))
                distribution.crons.STATE['UPCOMING'] = localtime(
                    now()).replace(
                        year=2019,
                        month=4,
                        day=5,
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())
                self._fast_forward_cron(frozen_datetime, 1, seconds=1)
                for x in [y for y in active if y != inactive]:
                    balances[x] += round(
                        settings.DISTRIBUTION_THROUGHPUT / (len(active)) * 0.4
                        +
                        settings.DISTRIBUTION_THROUGHPUT / (len(active)) * 0.3
                        + settings.DISTRIBUTION_THROUGHPUT / (len(active) - 1)
                        * 0.2 + settings.DISTRIBUTION_THROUGHPUT /
                        (len(active) + 1) * 0.1, )
                self._fast_forward_cron(frozen_datetime, 1, seconds=59)
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                # everybody drops off and one person joins
                for x in inactive:
                    self._do_transfer(x)
                self._fast_forward_cron(
                    frozen_datetime, 60 * 24 * 7, minutes=1)
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())

                new_3 = ibis.models.Person.objects.create(
                    username=str(random.random()))
                amount = settings.DISTRIBUTION_THROUGHPUT * 0.4 + \
                    settings.DISTRIBUTION_THROUGHPUT / (
                        len(active)) * 0.3 + settings.DISTRIBUTION_THROUGHPUT / (
                        len(active)) * 0.2 + settings.DISTRIBUTION_THROUGHPUT / (
                            len(active) - 1) * 0.1
                balances[new_3] = round(
                    amount * settings.DISTRIBUTION_THROUGHPUT /
                    (settings.DISTRIBUTION_THROUGHPUT + amount))
                assert all(balances[x] == x.balance()
                           for x in ibis.models.Person.objects.all())
