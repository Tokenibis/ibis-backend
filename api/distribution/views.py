import logging
import ibis.models
import distribution.models as models

from django.db import transaction
from .payments import PayPalClient
from django.conf import settings
from django.utils.timezone import localtime
from graphql_relay.node.node import to_global_id
from django.views.generic.list import ListView
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import generics, response, exceptions

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


class PaymentView(generics.GenericAPIView):
    serializer_class = ibis.serializers.PaymentSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paypal_client = PayPalClient()

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")
        description, net, fee = self.paypal_client.get_order(
            request.data['orderID'])

        if not (description and net):
            logger.error('Error fetching order information')
            return response.Response({
                'depositID': '',
            })

        user = ibis.models.User.objects.get(pk=request.user.id)

        date = localtime().date()

        with transaction.atomic():
            deposit = ibis.models.Deposit.objects.create(
                user=user,
                amount=net,
                description='paypal:{}:{}'.format(fee, description),
                category=ibis.models.ExchangeCategory.objects.get(
                    title='paypal'),
            )

            models.Investment.objects.create(
                name=str(user),
                amount=net,
                start=date,
                end=date,
                description='On-app deposit',
                deposit=deposit,
            )

        return response.Response({
            'depositID':
            to_global_id('DepositNode', deposit.id),
        })


class InvestmentView(ListView):
    template_name = 'investment_list.html'
    model = models.Investment
    paginate_by = 50
    ordering = ['-start']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    @xframe_options_exempt
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
