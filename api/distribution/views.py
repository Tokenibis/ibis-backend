import logging
import ibis.models
import distribution.models as models

from django.db.models import Sum
from django.utils.timezone import localtime
from rest_framework import generics, response

logger = logging.getLogger(__name__)


class FinanceView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):

        time = localtime()

        return response.Response({
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
