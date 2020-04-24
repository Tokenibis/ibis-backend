import random

from hashlib import sha256

from django.db import models
from django.conf import settings
from django.utils.timezone import now, localtime, timedelta
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


class Distributor(models.Model):

    person = AutoOneToOneField(
        ibis.models.Person,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    eligible = models.BooleanField(default=True)

    def is_active(self):
        previous_list, _ = models.Distributor._get_times(now())
        return self.transaction_to.filter(created__gt=previous_list[-1]).union(
            self.donation_to.filter(created__gt=previous_list[-1])).exists()

    def distribute_initial(self):
        if not self.eligible:
            raise ValueError('Person is not eligible for distribution program')

        current = now()
        previous_list, upcoming = Distributor._get_times(current)

        self._distribute(
            Distributor.get_distribution_amount(previous_list, initial=True),
            current,
        )

    def _distribute(self, amount, current):
        if not amount:
            return

        ibis.models.Deposit.objects.create(
            user=self.person,
            amount=amount,
            payment_id='ubp:{}'.format(
                sha256(str(random.random()).encode('utf-8')).hexdigest()),
            category=ibis.models.DepositCategory.objects.get(title='ubp'),
            created=localtime(current),
        )

    @staticmethod
    def distribute_all_safe():
        current = now()
        previous_list, upcoming = Distributor._get_times(current)

        amount = Distributor.get_distribution_amount(previous_list)

        for participant in list(
                Distributor._get_participants(
                    previous_list[-2],
                    previous_list[-1],
                )):
            if not participant.deposit_set.filter(
                    created__gte=previous_list[-1],
                    category=ibis.models.DepositCategory.objects.get(
                        title='ubp'),
            ).exists():
                participant.distributor._distribute(amount, current)

        return upcoming

    @staticmethod
    def get_distribution_amount(previous_list, initial=False):
        combined_amount = 0
        for i in range(len(previous_list) - 1):
            if Distributor._get_distributions(
                    previous_list[i],
                    previous_list[i + 1],
            ).exists():
                number = Distributor._get_participants(
                    previous_list[i],
                    previous_list[i + 1],
                ).count()
                if number:
                    amount = settings.DISTRIBUTION_THROUGHPUT / number
                else:
                    amount = settings.DISTRIBUTION_THROUGHPUT
            else:
                amount = settings.DISTRIBUTION_DEFAULT
            combined_amount += amount * (i + 1) / sum(
                range(len(previous_list)))

        if initial and combined_amount:
            combined_amount = combined_amount * (
                settings.DISTRIBUTION_THROUGHPUT / combined_amount) / (
                    settings.DISTRIBUTION_THROUGHPUT / combined_amount +
                    ibis.models.Person.objects.filter(
                        date_joined__gte=previous_list[-1]).count())

        return round(combined_amount)

    @staticmethod
    def _get_participants(start, end):
        return ibis.models.Person.objects.exclude(
            distributor__eligible=False).filter(
                id__in=(ibis.models.Donation.objects.filter(
                    created__gt=start,
                    created__lte=end,
                ).values('user').union(
                    ibis.models.Transaction.objects.filter(
                        created__gt=start,
                        created__lte=end,
                    ).values('user')).distinct()))

    @staticmethod
    def _get_distributions(start, end):
        return ibis.models.Deposit.objects.filter(
            created__gt=start,
            created__lte=end,
            category=ibis.models.DepositCategory.objects.get(title='ubp'),
        )

    @staticmethod
    def _get_times(current):

        current_day_start = localtime(current).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        previous_list = list(
            reversed([
                current_day_start - timedelta(
                    days=((current_day_start.weekday() -
                           DAYS.index(settings.DISTRIBUTION_DAY)) % len(DAYS)))
                - timedelta(days=i * len(DAYS)) for i in range(0, 5)
            ]))

        upcoming = current_day_start + timedelta(
            days=((DAYS.index(settings.DISTRIBUTION_DAY) -
                   current_day_start.weekday() - 1) % len(DAYS)) + 1)

        return previous_list, upcoming
