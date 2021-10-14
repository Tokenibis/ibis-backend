import math
import logging
import ibis.models
import distribution.models as models

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.timezone import localtime
from rest_framework import generics, response

logger = logging.getLogger(__name__)


def _month(x, offset=0):
    return x.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        month=(x.month - 1 + offset) % 12 + 1,
        year=x.year + math.floor((x.month - 1 + offset) / 12),
    )


class FinanceView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):

        time = localtime()

        return response.Response({
            'monthly_donations': ['{}-{}: ${:.2f} ({} donations)'.format(
                time.year + math.floor((time.month - 1 + i) / 12),
                (time.month - 1 + i) % 12 + 1,
                ibis.models.Donation.objects.filter(
                    created__gte=_month(time, i),
                    created__lt=_month(time, i + 1),
                ).aggregate(amount=Coalesce(
                    Sum('amount'),
                    0,
                ))['amount'] / 100,
                ibis.models.Donation.objects.filter(
                    created__gte=_month(time, i),
                    created__lt=_month(time, i + 1),
                ).count(),
            ) for i in range(0, -12, -1)],
            'total_grants':
            '${:.2f}'.format(
                ibis.models.Grant.objects.aggregate(
                    Sum('amount'))['amount__sum'] / 100),
            'total_donations':
            '${:.2f}'.format(
                ibis.models.Donation.objects.aggregate(
                    Sum('amount'))['amount__sum'] / 100),
            'total_withdrawals':
            '${:.2f}'.format(
                ibis.models.Withdrawal.objects.aggregate(
                    Sum('amount'))['amount__sum'] / 100),
            'upcoming_goals': [(
                str(models.to_step_start(time, offset=x).date()),
                '${:.2f}'.format(
                    models.Goal.amount_static(time, offset=x) / 100),
            ) for x in range(8)],
            'accumulated_error':
            '${:.2f}'.format((ibis.models.Donation.objects.filter(
                created__gte=models.to_step_start(
                    models.Goal.objects.order_by('created').first().created),
                created__lt=models.to_step_start(time)).aggregate(
                    Sum('amount'))['amount__sum'] - sum(
                        x.amount() for x in models.Goal.objects.all())) / 100),
        })
