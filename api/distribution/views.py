import logging
import ibis.models
import distribution.models as models

from django.conf import settings
from django.utils.timezone import localtime
from rest_framework import generics, response

logger = logging.getLogger(__name__)


class AmountView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        time = localtime()
        total_amount = models.get_distribution_amount(time)
        shares = models.get_distribution_shares(time)
        max_share = max(shares.values())

        weekly_amount = round(total_amount * max_share)
        initial_amount = round(
            total_amount * max_share / (1 + max_share) *
            (len(shares) / (ibis.models.Deposit.objects.filter(
                created__gte=models.to_step_start(time),
                category=ibis.models.ExchangeCategory.objects.get(
                    title=settings.IBIS_CATEGORY_UBP),
            ).count() + 1)))

        if ibis.models.Donation.objects.filter(
                created__gte=models.to_step_start(time, offset=-1),
                created__lt=models.to_step_start(time),
        ) or ibis.models.Person.objects.filter(
                created__gte=models.to_step_start(time, offset=-1),
                created__lt=models.to_step_start(time),
        ):
            exact = True
        else:
            exact = False

        return response.Response({
            'weekly_amount':
            weekly_amount,
            'weekly_amount_str':
            '${:.2f}'.format(weekly_amount / 100),
            'weekly_time':
            models.to_step_start(time),
            'initial_amount':
            initial_amount,
            'initial_amount_str':
            '${:.2f}'.format(initial_amount / 100),
            'initial_time':
            time,
            'exact_amounts':
            exact,
        })
