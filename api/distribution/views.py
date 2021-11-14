import os
import math
import logging
import ibis.models
import ibis.schema
import matplotlib.pyplot as plt
import distribution.models as models

from lxml import etree
from io import StringIO
from django.db.models import Sum
from django.conf import settings
from django.db.models.functions import Coalesce
from django.utils.timezone import localtime
from django.views.generic.detail import DetailView
from rest_framework import generics, response
from graphql_relay.node.node import to_global_id
from django.views.decorators.clickjacking import xframe_options_exempt

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


class AmountView(generics.GenericAPIView):
    @xframe_options_exempt
    def get(self, request, *args, **kwargs):
        time = localtime()

        return response.Response({
            'initial':
            '${:,.2f}'.format(models.get_distribution_initial(time) / 100),
            'total':
            '${:,.2f}'.format(models.get_distribution_amount(time) / 100),
            'weekly':
            '${:,.2f}'.format(
                models.get_distribution_amount(time) *
                max(models.get_distribution_shares(time).values()) / 100),
        })


class FinanceView(generics.GenericAPIView):
    @xframe_options_exempt
    def get(self, request, *args, **kwargs):
        time = localtime()

        return response.Response({
            'monthly_donations': [
                '{}-{}: ${:,.2f} ({} donations)'.format(
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
                ) for i in range(0, -12, -1)
            ],
            'total_grants':
            '${:,.2f}'.format(
                ibis.models.Grant.objects.aggregate(
                    Sum('amount'))['amount__sum'] / 100),
            'total_donations':
            '${:,.2f}'.format(
                ibis.models.Donation.objects.aggregate(
                    Sum('amount'))['amount__sum'] / 100),
            'total_withdrawals':
            '${:,.2f}'.format(
                ibis.models.Withdrawal.objects.aggregate(
                    Sum('amount'))['amount__sum'] / 100),
            'number_donations':
            '{:,}'.format(ibis.models.Donation.objects.count()),
            'number_donors':
            '{:,}'.format(
                ibis.models.Donation.objects.values_list(
                    'user').distinct().count()),
            'upcoming_goals': [(
                str(models.to_step_start(time, offset=x).date()),
                '${:,.2f}'.format(
                    models.Goal.amount_static(time, offset=x) / 100),
            ) for x in range(8)],
            'accumulated_error':
            '${:,.2f}'.format((ibis.models.Donation.objects.filter(
                created__gte=models.to_step_start(
                    models.Goal.objects.order_by('created').first().created),
                created__lt=models.to_step_start(time)).aggregate(
                    Sum('amount'))['amount__sum'] -
                               sum(x.amount()
                                   for x in models.Goal.objects.all())) / 100),
        })


class ReportView(DetailView):
    template_name = 'report.html'

    model = ibis.models.Grant

    def get_context_data(self, **kwargs):
        grant = ibis.models.Grant.objects.get(pk=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['amount_str'] = '${:,.2f}'.format(grant.amount / 100)

        with open(os.path.join(
                settings.MEDIA_ROOT,
                'circles',
                'static.svg',
        )) as fd:
            circles = etree.fromstring(fd.read().encode('utf-8'))

        stops = {
            'url(#{})'.format(x.attrib['id']): x.getchildren()[1]
            for x in circles.getchildren()[0].getchildren()
        }

        grant_id = to_global_id(ibis.schema.GrantNode.__name__, grant.id)

        for c in circles.getchildren()[1:]:
            if c.attrib.get('grant') == grant_id:
                pass
                # stops[c.attrib['fill']].attrib['stop-color'] = '#ffff00'
            elif c.attrib['id'] == grant_id:
                stops[c.attrib['fill']].attrib['stop-color'] = '#3b3b3b'
            else:
                c.attrib['opacity'] = '0.4'

        circles.attrib['id'] = 'circles'
        context['circles'] = etree.tostring(circles).decode()

        # stacked bar chart
        graph = StringIO()
        plt.plot([0, 1], [5, 7])
        plt.savefig(graph, format='svg')
        plt.clf()
        context['distribution'] = graph.getvalue()

        # pie chart
        graph = StringIO()
        plt.plot([0, 1], [5, 7])
        plt.savefig(graph, format='svg')
        plt.clf()
        context['donations'] = graph.getvalue()

        context['grantdonation'] = [{
            'amount':
            '${:,.2f}'.format(x.amount / 100),
            'donation':
            x.donation,
            'reply':
            x.donation.parent_of.order_by('-created').filter(
                user=x.donation.target).first(),
        } for x in grant.grantdonation_set.order_by('donation__created')]

        return context
