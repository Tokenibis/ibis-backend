import os
import math
import logging
import ibis.models
import ibis.schema
import matplotlib.pyplot as plt
import distribution.models as models

from collections import defaultdict
from lxml import etree
from io import StringIO
from django.db.models import Sum
from django.conf import settings
from django.db.models.functions import Coalesce
from django.utils.timezone import localtime
from django.views.generic.base import TemplateView
from rest_framework import generics, response
from graphql_relay.node.node import to_global_id
from django.views.decorators.clickjacking import xframe_options_exempt
from matplotlib.ticker import StrMethodFormatter

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
            'balance':
            '${:,.2f}'.format(
                ibis.models.Grant.objects.aggregate(Sum(
                    'amount'))['amount__sum'] / 100 -
                ibis.models.Withdrawal.objects.aggregate(Sum(
                    'amount'))['amount__sum'] / 100),
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


class ReportView(TemplateView):
    template_name = 'report.html'

    model = ibis.models.Grant

    def get_context_data(self, **kwargs):
        grant = ibis.models.Grant.objects.order_by('created')[
            int(self.kwargs['number']) - 1]
        context = super().get_context_data(**kwargs)
        weekly = grant.amount / grant.duration / 100

        # --- create icons ---

        icon = '<svg class="icon" viewBox="0 0 24 24"><path d="{}"></path></svg>'
        context['grant_icon'] = icon.format(
            'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1.41 16.09V20h-2.67v-1.93c-1.71-.36-3.16-1.46-3.27-3.4h1.96c.1 1.05.82 1.87 2.65 1.87 1.96 0 2.4-.98 2.4-1.59 0-.83-.44-1.61-2.67-2.14-2.48-.6-4.18-1.62-4.18-3.67 0-1.72 1.39-2.84 3.11-3.21V4h2.67v1.95c1.86.45 2.79 1.86 2.85 3.39H14.3c-.05-1.11-.64-1.87-2.22-1.87-1.5 0-2.4.68-2.4 1.64 0 .84.65 1.39 2.67 1.91s4.18 1.39 4.18 3.91c-.01 1.83-1.38 2.83-3.12 3.16z'
        )
        context['person_icon'] = icon.format(
            'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z'
        )
        context['organization_icon'] = icon.format(
            'M20 4H4v2h16V4zm1 10v-2l-1-5H4l-1 5v2h1v6h10v-6h4v6h2v-6h1zm-9 4H6v-4h6v4z'
        )
        context['donation_icon'] = icon.format(
            'M20 6h-2.18c.11-.31.18-.65.18-1 0-1.66-1.34-3-3-3-1.05 0-1.96.54-2.5 1.35l-.5.67-.5-.68C10.96 2.54 10.05 2 9 2 7.34 2 6 3.34 6 5c0 .35.07.69.18 1H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-5-2c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zM9 4c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm11 15H4v-2h16v2zm0-5H4V8h5.08L7 10.83 8.62 12 11 8.76l1-1.36 1 1.36L15.38 12 17 10.83 14.92 8H20v6z'
        )

        context['ibis_icon'] = '''
        <svg id="ibis-icon" viewBox="0 0 758.66 725.75"><path d="m 489.74,147 c -0.47,0.69 -7.58,0.29 -8.45,0.35 A 214.14,214.14 0 0 0 458.43,150.27 244.19,244.19 0 0 0 386.7,175 c -14.36,7.66 -25.21,14.59 -37.58,25.16 -13.29,11.37 -30,29.22 -41,42.72 a 328.89,328.89 0 0 0 -33.21,48.69 377.26,377.26 0 0 0 -41.38,113.63 c -1.13,5.78 -2.12,11.59 -3.08,17.41 -0.63,3.82 -1.47,9.27 -1.87,13.18 -0.81,7.81 3.83,6.49 5.48,-1.33 0,0 14.1,-52.93 36,-94 21.9,-41.07 68.09,-105.9 171.6,-133.35 0,0 67.86,-17.53 86.93,0.24 19.07,17.77 5.36,47.76 5.36,47.76 0,0 -10.27,22.48 -32.63,47.9 -22.36,25.42 -70.56,72.78 -70.32,140.13 0.24,67.35 41.3,111.52 77.66,136.13 39,26.41 86.14,40.05 132.83,43.72 a 310.78,310.78 0 0 0 71.34,-2.46 c 12.47,-1.9 25.24,-4.31 37.18,-8.46 2.5,-0.87 21.81,-6.71 15.47,-12.49 -5.8,-5.28 -80.07,-13.51 -75.13,-75.12 0,0 3.21,-64.49 78.06,-59 43.91,3.21 68.78,50.28 71,97.16 2.26,47.43 -11.9,86.46 -39.28,123.82 -53.3,72.73 -132.25,108 -224,106.79 C 486.27,792 366.46,751.81 306.6,678.14 292.09,660.28 292.36,661 279.81,643 c -4.27,-6.15 -10.3,-15.43 -17.58,-28.47 -7.16,-12.84 -7.72,-19.53 -11.9,-19.81 -3.7,-0.25 -1.12,11.16 1.48,18 A 369.94,369.94 0 0 0 351,757 c 139,124.18 368.53,131.23 503,-13 36.94,-39.62 56.88,-89.84 66.93,-139 0,0 42.42,-166.32 -99.56,-301.85 0,0 -72.63,-61.86 -150.55,-75 0,0 -17.6,-5 -16.68,15.14 0,0 18.55,148.3 -112,170.57 0,0 -64.43,9.46 -32.06,-62.66 13.28,-29.59 39.23,-50.86 54.08,-79.52 14.85,-28.66 24.1,-60.64 25.59,-92.93 0.29,-6.24 0.28,-12.5 0,-18.74 l -1.12,-23.91 c 0,0 -1.24,-10.78 -12.55,-10.74 -11.31,0.04 -68.21,5.84 -68.21,5.84 0,0 -6,0 -9.66,3.76 -3.66,3.76 -6.21,8.79 -8.47,12.04 z m 235.48,3.35 c -7.56,3.4 -14.91,7.22 -22.38,11 l -28.77,14.57 a 4.67,4.67 0 0 0 -3,3.83 c -0.54,5.06 5.7,4.76 9.22,5.4 3.21,0.59 6.4,1.27 9.57,2 22.2,5.19 52.85,15.27 73.62,26 a 518.72,518.72 0 0 1 48.87,29.14 c 22.58,15.51 38.21,27.77 51.6,42.3 1.23,1.34 12.21,14.25 13.39,15.63 52.47,61.39 80.38,125 83.72,215.44 2,53.59 -22.54,127.88 -48.5,177.92 a 1.76,1.76 0 0 0 1.87,2.55 c 1.93,-0.36 3.86,-2.33 7.56,-8 40.64,-62.16 66.18,-140 65.07,-214.43 a 314.37,314.37 0 0 0 -7.32,-61.12 c -8.89,-41.38 -24.07,-83.11 -47.32,-118.64 -7.61,-11.64 -18.35,-27.8 -27.2,-38.52 a 394.17,394.17 0 0 0 -30.79,-33.17 425.17,425.17 0 0 0 -37.5,-32 c -14.35,-10.9 -31.15,-20.61 -46.65,-29.8 -8.41,-5 -16.81,-10 -25.64,-14.26 -7.19,-3.44 -14.28,-5.61 -22.16,-2.61 -0.36,0.14 -0.72,0.27 -1.09,0.39 a 159.52,159.52 0 0 0 -16.17,6.38 z" transform="translate(-228.48 -125.42)"></path></svg>
        '''

        # --- format circles graphic ---

        SCALE = 0.02

        with open(os.path.join(
                settings.MEDIA_ROOT,
                'circles',
                'simple.svg',
        )) as fd:
            circles = etree.fromstring(fd.read().encode('utf-8'))

        grant_id = to_global_id(ibis.schema.GrantNode.__name__, grant.id)

        # Remove circles that took place after the focus grant ended

        last = grant.grantdonation_set.order_by('donation__created').last()

        delete_set = set([
            to_global_id(ibis.schema.GrantNode.__name__, x[0])
            for x in ibis.models.Grant.objects.filter(
                created__gt=grant.created).values_list('id')
        ] + [
            to_global_id(ibis.schema.GrantDonationNode.__name__, x[0])
            for x in ibis.models.GrantDonation.objects.filter(
                donation__created__gte=last.donation.created).exclude(
                    id=last.id).values_list('id')
        ])

        delete_list = [
            c for c in circles.getchildren()[1:]
            if c.attrib['id'] in delete_set
        ]
        for c in delete_list:
            circles.remove(c)

        # Highlight focus circles

        highlighted = []

        for c in circles.getchildren()[1:]:
            if c.attrib.get('grant') == grant_id:
                highlighted.append(c)
            elif c.attrib['id'] == grant_id:
                grant_circle = c
                c.attrib['fill'] = '#3b3b3b'
            elif c.attrib.get('grant'):
                c.attrib['opacity'] = '0.25'
            else:
                c.attrib['opacity'] = '0.25'
                c.attrib['fill'] = '#9b9b9b'

        scale = max(
            1,
            math.sqrt(SCALE) / (math.sqrt(grant.amount) / math.sqrt(
                ibis.models.Grant.objects.filter(created__lte=grant.created).
                aggregate(Sum('amount'))['amount__sum'])),
        )

        def _translate(c):
            c.attrib['r'] = str(float(c.attrib['r']) * scale)
            c.attrib['opacity'] = str(0.5 / scale + 0.5)
            for a in ['cy', 'cx']:
                c.attrib[a] = str((float(c.attrib[a]) -
                                   float(grant_circle.attrib[a])) * scale +
                                  float(grant_circle.attrib[a]))

        for c in [grant_circle] + highlighted:
            _translate(c)

        # set final display parameters

        border = {
            'top': -float('inf'),
            'bottom': float('inf'),
            'left': float('inf'),
            'right': -float('inf'),
        }

        for c in circles.getchildren()[1:]:
            if float(c.attrib['cy']) + float(c.attrib['r']) > border['top']:
                border['top'] = float(c.attrib['cy']) + float(c.attrib['r'])
            if float(c.attrib['cy']) - float(c.attrib['r']) < border['bottom']:
                border['bottom'] = float(c.attrib['cy']) - float(c.attrib['r'])
            if float(c.attrib['cx']) - float(c.attrib['r']) < border['left']:
                border['left'] = float(c.attrib['cx']) - float(c.attrib['r'])
            if float(c.attrib['cx']) + float(c.attrib['r']) > border['right']:
                border['right'] = float(c.attrib['cx']) + float(c.attrib['r'])

        circles.attrib['viewBox'] = '{} {} {} {}'.format(
            border['left'],
            border['bottom'],
            border['right'] - border['left'],
            border['top'] - border['bottom'],
        )

        circles.attrib['id'] = 'circles'
        context['circles'] = etree.tostring(circles).decode()

        # --- ubp distribution bar chart ---

        OFFSET = 2

        raw = [[
            str(
                models.to_step_start(
                    grant.created,
                    offset=i - OFFSET + 1,
                ).date()),
            models.Goal.breakdown_static(
                grant.created,
                offset=i - OFFSET + 1,
            ),
        ] for i in range(grant.duration + OFFSET)]

        grants = sorted(
            set(grant for _, breakdown in raw for grant in breakdown),
            key=lambda x: float('inf')
            if x == grant else x.created.timestamp(),
        )

        data = [(
            date,
            list(
                reversed([
                    sum(breakdown[g] / 100 for g in grants[:i + 1]
                        if g in breakdown) for i in range(len(grants))
                ])),
        ) for date, breakdown in raw]

        graph = StringIO()
        _, ax = plt.subplots(figsize=(4, 3))

        for i in range(len(grants)):
            plt.bar(
                [x[0] for x in data],
                [x[1][i] for x in data],
                color='#84ab3f' if i == 0 else '#c2d59f',
                edgecolor='w',
            )

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.set_major_formatter(StrMethodFormatter('${x:0.0f}'))
        ax.set_xticks([], [])
        plt.xticks(rotation=45),
        plt.savefig(graph, format='svg', bbox_inches='tight')
        plt.clf()
        context['distribution'] = graph.getvalue()

        # --- organizations pie chart ---

        NUM_LABELS = 16

        fundraised = defaultdict(lambda: 0)
        for x in grant.grantdonation_set.all():
            fundraised[x.donation.target] += x.amount
        fundraised = sorted(
            fundraised.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        def _color(value, fraction):
            return value + round((1 - fraction) * (255 - value))

        graph = StringIO()

        plt.subplots(figsize=(4.6, 4.6))
        patches, texts = plt.pie(
            [x[1] for x in fundraised],
            radius=1,
            colors=[
                '#%02X%02X%02X' % (
                    _color(132, a / fundraised[0][1]),
                    _color(171, a / fundraised[0][1]),
                    _color(63, a / fundraised[0][1]),
                ) for _, a in fundraised
            ],
            startangle=90,
            counterclock=False,
            wedgeprops={
                'edgecolor': 'w',
                'linewidth': 1
            },
        )
        plt.axis('equal')

        circle = plt.Circle((0, 0), 0.5, color='white')
        plt.gcf().gca().add_artist(circle)

        def _truncate(x):
            LIMIT = 32
            return (str(x)[:LIMIT - 3] +
                    '...') if len(str(x)) > LIMIT else str(x)

        plt.legend(
            patches[:NUM_LABELS],
            labels=[_truncate(x[0]) for x in fundraised[:NUM_LABELS - 1]] +
            (['...'] if len(fundraised) > NUM_LABELS else
             [_truncate(fundraised[min(NUM_LABELS, len(fundraised)) - 1][0])]),
            bbox_to_anchor=(1.0, 1.0),
            frameon=False,
        )
        plt.savefig(graph, format='svg', bbox_inches='tight')
        plt.clf()
        context['organizations'] = graph.getvalue()

        # --- set final context ---

        context['grantdonation'] = [{
            'amount':
            '${:,.2f}'.format(x.amount / 100),
            'donation':
            x.donation,
            'reply':
            x.donation.parent_of.order_by('-created').filter(
                user=x.donation.target).first(),
        } for x in grant.grantdonation_set.order_by('donation__created')]

        context['amount_str'] = '${:,.0f}'.format(
            grant.amount / 100) if grant.amount / 100 == int(
                grant.amount / 100) else '${:,.2f}'.format(grant.amount / 100)
        context['weekly_str'] = '${:,.0f}'.format(weekly) if weekly == int(
            weekly) else '${:,.2f}'.format(weekly)
        context['object'] = grant
        context['number'] = self.kwargs['number']
        context['number_suffix'] = 'st' if int(
            self.kwargs['number']) % 10 == 1 else (
                'nd' if int(self.kwargs['number']) % 10 == 2 else 'th')
        context['num_donations'] = grant.grantdonation_set.count()
        context['num_organizations'] = len(
            set(grant.grantdonation_set.values_list('donation__target')))
        context['num_people'] = len(
            set(grant.grantdonation_set.values_list('donation__user')))
        context['progress'] = round(
            sum(x.amount
                for x in grant.grantdonation_set.all()) / grant.amount * 100)
        context['culmulative_str'] = '${:,.2f}'.format(
            ibis.models.Donation.objects.filter(
                created__lte=last.donation.created).aggregate(
                    Sum('amount'))['amount__sum'] / 100)
        context['end'] = last.donation.created
        context['link'] = settings.DONATE_LINK

        return context


class LogoView(TemplateView):
    template_name = 'logos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = sorted(
            [x for x in ibis.models.Organization.objects.filter(is_active=True)],
            key=lambda x: x.date_joined,
        )
        return context
