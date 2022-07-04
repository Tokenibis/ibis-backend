import os
import math
import json
import logging
import markdown
import ibis.models
import ibis.schema
import distribution.models as models
import distribution.circles as circles
import distribution.graph as graph

from django.views.generic.list import ListView
from django.views.generic.base import TemplateView
from django.db.models import Sum
from django.conf import settings
from django.db.models.functions import Coalesce
from django.utils.timezone import localtime
from rest_framework import generics, response
from graphql_relay.node.node import from_global_id, to_global_id
from django.views.decorators.clickjacking import xframe_options_exempt

logger = logging.getLogger(__name__)

DIR = os.path.dirname(os.path.realpath(__file__))

ICONS = {}
for root, dirs, files in os.walk(os.path.join(DIR, 'icons')):
    for filename in files:
        with open(os.path.join(root, filename)) as fd:
            ICONS[filename.rsplit('.', 1)[0]] = fd.read()


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


class GrantView(ListView):
    template_name = 'grants.html'
    model = ibis.models.Grant
    paginate_by = 50
    ordering = ['-created']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_link'] = '{}/distribution/report?id='.format(
            settings.API_ROOT_PATH)
        context['report_generic'] = '{}/distribution/report'.format(
            settings.API_ROOT_PATH)
        context['amount_str'] = '${:,.2f}'.format(
            ibis.models.Donation.objects.all().aggregate(
                Sum('amount'))['amount__sum'] / 100)
        return context

    @xframe_options_exempt
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class ReportView(TemplateView):
    template_name = 'report.html'

    model = ibis.models.Grant

    @xframe_options_exempt
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['icons'] = ICONS

        if 'id' in self.request.GET:
            return self.get_specific_context(context)
        else:
            return self.get_general_context(context)

    def get_general_context(self, context):
        launch = ibis.models.Donation.objects.order_by(
            'created').first().created

        context['title'] = 'The Token Ibis Project'
        context['progress'] = 100
        context['num_grants'] = ibis.models.Grant.objects.count()
        context['num_donations'] = ibis.models.Donation.objects.count()
        context['num_people'] = ibis.models.Donation.objects.all().values_list(
            'user', flat=True).distinct().count()
        context['num_organizations'] = ibis.models.Organization.objects.filter(
            is_active=True).count()
        context['now'] = localtime()
        context['amount_str'] = '${:,.2f}'.format(
            ibis.models.Donation.objects.all().aggregate(
                Sum('amount'))['amount__sum'] / 100)

        with open(os.path.join(
                settings.MEDIA_ROOT,
                'graphs',
                'payout.svg',
        )) as fd:
            context['payout'] = fd.read()

        with open(
                os.path.join(
                    settings.MEDIA_ROOT,
                    'graphs',
                    'distribution.svg',
                )) as fd:
            context['distribution'] = fd.read()

        context['circles'] = circles.load_circles()

        context['grantdonation'] = [{
            'amount':
            '${:,.2f}'.format(x.amount / 100),
            'donation':
            x,
            'reply':
            x.parent_of.order_by('-created').first(),
        } for x in ibis.models.Donation.objects.order_by('-created')[:100]]

        context['section_1'] = markdown.markdown('''
On __{date}__, Token Ibis launched the world's first-ever pilot project for Universal Basic Philanthropy&ndash;right here in the city of Albuquerque.

Operating on nothing more than few computers, a PO box, and a dedicated team of volunteers, Token Ibis has established strong ties with __{organizations} different organizations__.
The pie chart on the right shows the full funding breakdown.
        '''.format(
            date=launch.strftime('%B %-d, %Y'),
            organizations=context['num_organizations'],
        ))

        context['section_2'] = markdown.markdown('''
In the __{weeks} weeks__ since our launch, our automated platform has worked without fail to place money in the hands of socially-minded members of the community.
The chart on the right shows the weekly target donations in gray, which is determined by incoming grants, compared with the actual donations, which is determined by the community.
        
Overall, grants to Token Ibis have empowered __{people:,} unique individuals__ to make __{donations:,} total donations__&ndash;{donations:,} personal decisions that tell us what the community truly needs.
        '''.format(
            weeks=round((context['now'] - launch).days / 7),
            people=context['num_people'],
            donations=context['num_donations'],
        ))

        context['section_3'] = markdown.markdown('''
With funding from __{grants} grants__, Token Ibis has facilitated __{amount}__ of democratic, community-centric donations.

The picture on the right is a snapshot of our platform's total impact at the time that the community finished spending this grant.
The gray circles are grants and the green circles clustered around them are the donations that they funded.
The picture will continue to grow, but as of __{date}__, these chapters are forever locked into the story Universal Basic Philanthropy.

You can support the movement at [{link}](https://{link}).
        '''.format(
            grants=context['num_grants'],
            amount=context['amount_str'],
            date=context['now'].strftime('%B %-d, %Y, %-I:%M %p'),
            link=settings.DONATE_LINK,
        ))

        return context

    def get_specific_context(self, context):
        grant = ibis.models.Grant.objects.get(
            id=from_global_id(self.request.GET['id'])[1])
        weekly = grant.amount / grant.duration / 100
        number = ibis.models.Grant.objects.filter(
            created__lte=grant.created).count()
        last = grant.grantdonation_set.order_by('donation__created').last()

        context['title'] = grant.name
        context['number'] = number
        context['amount_str'] = '${:,.0f}'.format(
            grant.amount / 100) if grant.amount / 100 == int(
                grant.amount / 100) else '${:,.2f}'.format(grant.amount / 100)
        context['object'] = grant
        context['num_grants'] = len([grant])
        context['num_donations'] = grant.grantdonation_set.count()
        context['num_organizations'] = len(
            set(grant.grantdonation_set.values_list('donation__target')))
        context['num_people'] = len(
            set(grant.grantdonation_set.values_list('donation__user')))
        context['progress'] = round(
            sum(x.amount
                for x in grant.grantdonation_set.all()) / grant.amount * 100)

        if not grant.grantdonation_set.exists():
            return context

        context['circles'] = circles.load_circles(grant)
        context['payout'] = graph.graph_grant_payout(grant)
        context['distribution'] = graph.graph_grant_distribution(grant)

        context['section_1'] = markdown.markdown('''
On __{date}__, {name} made a grant of __{amount}__ to build a better Albuquerque.

{name} trusted our team of volunteers to make sure that every penny of the grant would help local nonprofits right here in this city:
{blurb}
The pie chart on the right shows the full breakdown.
'''.format(
            date=grant.created.strftime('%B %-d, %Y'),
            name=grant.name,
            amount=context['amount_str'],
            blurb='__{} different organizations__ in total'.format(
                context['num_organizations'])
            if context['num_organizations'] > 1 else
            'in this case, one organization in particular.',
        ))

        weekly_str = '${:,.0f}'.format(weekly) if weekly == int(
            weekly) else '${:,.2f}'.format(weekly)

        context['section_2'] = markdown.markdown('''
{blurb1} and placed the money in the hands of socially-minded members of the community.
The bar chart on the right shows the added financial impact in dark green.

By the end, {name}'s grant funded
{blurb2} a personal act of decency that would never have happened otherwise.
It empowered {blurb3} heard in their community.
'''.format(
            blurb1=
            'Over __{} weeks,__ an algorithm divided it into __{}__ weekly portions'
            .format(grant.duration, weekly_str) if grant.duration > 1 else
            'In one week, an algorithm took the full grant',
            name=grant.name,
            blurb2='__{} different donations__, each one'.format(
                context['num_donations']) if context['num_donations'] > 1 else
            'another individual\'s donation',
            blurb3='__{} different individuals__ to make their voices'.format(
                context['num_people']) if context['num_people'] > 1 else
            'another person to make their voice',
        ))

        context['section_3'] = markdown.markdown('''
{name}'s grant is the __{ordinal} grant__ of its kind in history.
By the end, it grew the total impact of the Token Ibis community to __{culmulative}__.

The picture on the right is a snapshot of our platform's total impact at the time that the community finished spending this grant.
The gray circles are grants and the green circles clustered around them are the donations that they funded.
{name}'s grant is highlighted.
The picture will continue to grow, but as of __{last}__, this chapter is forever locked into the story Universal Basic Philanthropy.
        '''.format(
            name=grant.name,
            ordinal=str(number) + ('st' if number % 10 == 1 else
                                   ('nd' if number % 10 == 2 else 'th')),
            culmulative='${:,.2f}'.format(
                ibis.models.Donation.objects.filter(
                    created__lte=last.donation.created).aggregate(
                        Sum('amount'))['amount__sum'] / 100),
            last=last.donation.created.strftime('%B %-d, %Y, %-I:%M %p'),
        ))

        context['grantdonation'] = [{
            'amount':
            '${:,.2f}'.format(x.amount / 100),
            'donation':
            x.donation,
            'reply':
            x.donation.parent_of.order_by('-created').first(),
        } for x in grant.grantdonation_set.order_by('-donation__created')]

        context['section_4'] = markdown.markdown('''
Numbers and pictures on express a small part of the impact of {name}'s grant.
This final section below shows every donation&ndash;along with the verbal exchanges that they sparked&ndash;that was made possible by this grant.

The mission of Token Ibis is to making social impact accessible to everyone through Universal Basic Philanthropy.
You can continue to support the movement at [{link}](https://{link}).
        '''.format(
            name=grant.name,
            link=settings.DONATE_LINK,
        ))

        context['grantdonation'] = [{
            'amount':
            '${:,.2f}'.format(x.amount / 100),
            'donation':
            x.donation,
            'reply':
            x.donation.parent_of.order_by('-created').first(),
        } for x in grant.grantdonation_set.order_by('-donation__created')]

        return context


class LogoView(TemplateView):
    template_name = 'logos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = sorted(
            [
                x for x in ibis.models.Organization.objects.filter(
                    is_active=True)
            ],
            key=lambda x: x.date_joined,
        )
        return context


class VideoView(TemplateView):
    template_name = 'video.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['circles'] = '{}/circles/simple.svg'.format(settings.MEDIA_URL)
        context['music'] = '{}/circles/music.mp3'.format(settings.MEDIA_URL)

        context['num_donors'] = '{:,}'.format(
            ibis.models.Donation.objects.all().values_list(
                'user', flat=True).distinct().count())
        context['num_donations'] = '{:,}'.format(
            ibis.models.Donation.objects.count())

        with open(os.path.join(
                settings.MEDIA_ROOT,
                'circles',
                'info.json',
        )) as fd:
            context['info'] = json.load(fd)

        return context

    @xframe_options_exempt
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
