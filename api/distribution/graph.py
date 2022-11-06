import os
import csv
import math
import ibis
import distribution
import matplotlib.pyplot as plt
import distribution.models as models

from io import StringIO
from collections import defaultdict
from django.conf import settings
from matplotlib.ticker import StrMethodFormatter
from pathlib import Path
from django.db.models import Sum, Max
from django.db.models.functions import Coalesce
from django.utils.timezone import localtime

DIR = os.path.join(settings.MEDIA_ROOT, 'graphs')


def run():
    Path(DIR).mkdir(parents=True, exist_ok=True)

    graph_control_response()
    graph_organization_distribution()
    graph_organization_time()
    graph_users_time()
    graph_deposits_payout()


def graph_control_response():
    data = [(
        distribution.models.to_step_start(x.created),
        x.amount(),
        ibis.models.Donation.objects.filter(
            created__gte=distribution.models.to_step_start(x.created),
            created__lt=distribution.models.to_step_start(x.created, offset=1),
        ).aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
    ) for x in distribution.models.Goal.objects.order_by('created')][1:-1]

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    plt.step(
        [x[0] for x in data],
        [x[1] / 100 for x in data],
        color='#3b3b3b',
        label='Target Donations',
    )

    plt.plot(
        [x[0] for x in data],
        [x[2] / 100 for x in data],
        '#84ab3f',
        label='Actual Donations',
    )

    ax.set_ylim(ymin=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.set_major_formatter(StrMethodFormatter('${x:0.0f}'))
    plt.xticks(rotation=45)
    plt.savefig(
        os.path.join(DIR, 'payout.svg'),
        bbox_inches='tight',
    )
    plt.clf()


def graph_organization_distribution():
    NUM_LABELS = 16

    fundraised = sorted(
        [(
            x,
            x.fundraised(),
        ) for x in ibis.models.Organization.objects.all()],
        key=lambda x: x[1],
        reverse=True,
    )

    def _color(value, fraction):
        return value + round((1 - fraction) * (255 - value))

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
        return (str(x)[:LIMIT - 3] + '...') if len(str(x)) > LIMIT else str(x)

    plt.legend(
        handles=patches[:NUM_LABELS],
        labels=[_truncate(x[0]) for x in fundraised[:NUM_LABELS - 1]] +
        (['...'] if len(fundraised) > NUM_LABELS else
         [_truncate(fundraised[min(NUM_LABELS, len(fundraised)) - 1][0])]),
        bbox_to_anchor=(1.0, 1.0),
        frameon=False,
    )
    plt.savefig(
        fname=os.path.join(DIR, 'distribution.svg'),
        bbox_inches='tight',
    )
    plt.clf()


def graph_organization_time():
    now = localtime()

    length = 1 + round((models.to_step_start(now) - models.to_step_start(
        ibis.models.Donation.objects.order_by('created').first().created)).days
                       / 7)

    def _index(created):
        return length - round(
            (models.to_step_start(now) - models.to_step_start(created)).days /
            7) - 1

    data = {
        x: [0] * length
        for x in ibis.models.Organization.objects.filter(is_active=True)
    }

    x_axis = [
        models.to_step_start(now, offset=i) for i in range(-length + 1, 1)
    ]

    for x in ibis.models.Donation.objects.filter(created__lte=now):
        if x.target in data:
            data[x.target][_index(x.created)] += x.amount

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    for org, y in sorted(data.items(), key=lambda x: sum(x[1])):
        plt.plot(
            x_axis[2:-2],
            [(a + b + c + d + e) / 5 / 100 for a, b, c, d, e in zip(
                y[:-4],
                y[1:-3],
                y[2:-2],
                y[3:-1],
                y[4:],
            )],
            label=str(org),
        )

    ax.set_ylim(ymin=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.set_major_formatter(StrMethodFormatter('${x:0.0f}'))
    plt.xticks(rotation=45)
    plt.savefig(
        fname=os.path.join(DIR, 'time.svg'),
        bbox_inches='tight',
    )
    plt.clf()


def graph_organization_edges():
    orgs = list(
        ibis.models.Organization.objects.filter(
            is_active=True).order_by('date_joined'))
    graph = [[0 for _ in range(len(orgs))] for _ in range(len(orgs))]
    for person in ibis.models.Person.objects.all():
        profile = [
            ibis.models.Donation.objects.filter(
                user=person,
                target=org,
            ).aggregate(amount=Coalesce(Sum('amount'), 0))['amount']
            for org in orgs
        ]

        for i in range(len(orgs)):
            for j in range(len(profile)):
                graph[i][j] += math.sqrt(profile[i] * profile[j])

    for i, line in enumerate(graph):
        total = sum(line)
        for j, val in enumerate(line):
            line[j] = val / total if total else 0

    with open(os.path.join(
            DIR,
            'organization_edges.csv',
    ), 'w', newline='') as fd:
        writer = csv.writer(fd)
        writer.writerow([''] + [str(x) for x in orgs])
        for i, line in enumerate(graph):
            writer.writerow([str(orgs[i])] + line)


def graph_users_time():
    data = [(
        distribution.models.to_step_start(x.created),
        len(
            set(y.user for y in ibis.models.Donation.objects.filter(
                created__gte=distribution.models.to_step_start(x.created),
                created__lt=distribution.models.to_step_start(x.created,
                                                              offset=1),
            ))),
        len(
            set(y for y in ibis.models.Person.objects.filter(
                is_active=True,
                date_joined__lt=distribution.models.to_step_start(x.created,
                                                                  offset=1))
                if ibis.models.Donation.objects.filter(user=y).exists())),
    ) for x in distribution.models.Goal.objects.filter(
        created__gte=ibis.models.Donation.objects.order_by(
            'created').first().created).order_by('created')][1:-1]

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    plt.plot(
        [x[0] for x in data],
        [x[1] for x in data],
        '#3b3b3b',
        label='Active Users (Weekly)',
    )
    plt.plot(
        [x[0] for x in data],
        [x[2] for x in data],
        '#84ab3f',
        label='Total Users (Culmulative)',
    )

    ax.set_ylim(ymin=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xlabel('Date (weekly)')
    plt.ylabel('Number of Users')
    plt.xticks(rotation=45)
    plt.legend(frameon=False)
    plt.savefig(
        fname=os.path.join(DIR, 'users.svg'),
        bbox_inches='tight',
    )
    plt.clf()


def graph_organization_engagement(self):
    x_axis = [
        distribution.models.to_step_start(x.created)
        for x in distribution.models.Goal.objects.order_by('created')
    ]

    data = {
        'outreach': [],
        'comment': [],
        'none': [],
    }

    for a, b, c in zip(x_axis[:-2], x_axis[1:-1], x_axis[2:]):
        for org in ibis.models.Organization.objects.filter(
                is_active=True,
                date_joined__lt=a,
        ):
            amount = sum(x.amount for x in org.donation_set.filter(
                created__gte=b,
                created__lt=c,
            ))
            if org.news_set.filter(
                    created__gte=a,
                    created__lt=b,
            ).exists() or org.event_set.filter(
                    created__gte=a,
                    created__lt=b,
            ).exists():
                data['outreach'].append(amount)
            elif org.comment_set.filter(created__gte=a,
                                        created__lt=b).exists():
                data['comment'].append(amount)
            else:
                data['none'].append(amount)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    plt.bar(
        ['News/Event', 'Comment Only', 'None'],
        [
            sum(data[x]) / len(data[x]) / 100
            for x in ['outreach', 'comment', 'none']
        ],
    )

    ax.set_ylim(ymin=0)
    plt.ylabel('Average Weekly Revenue ($/Org)')
    plt.savefig(os.path.join(DIR, 'engagement.svg'))
    plt.clf()


def graph_finances_time():
    data = [(
        x,
        ibis.models.Grant.objects.filter(
            created__lt=distribution.models.to_step_start(x, offset=1)).
        aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
        ibis.models.Donation.objects.filter(
            created__lt=distribution.models.to_step_start(x, offset=1)).
        aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
        ibis.models.Withdrawal.objects.filter(
            created__lt=distribution.models.to_step_start(x, offset=1)
        ).aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
    ) for x in [
        distribution.models.to_step_start(
            ibis.models.Donation.objects.order_by('created').first().created,
            offset=i,
        ) for i in range(
            int((ibis.models.Donation.objects.order_by('created').last().
                 created - ibis.models.Donation.objects.order_by(
                     'created').first().created).days / 7))
    ]]

    _, ax = plt.subplots(figsize=(4, 3))

    plt.step(
        [x[0] for x in data],
        [int(x[1] or 0) / 100 for x in data],
        label='Culmulative Grants',
    )
    plt.step(
        [x[0] for x in data],
        [int(x[2] or 0) / 100 for x in data],
        label='Culmulative Donations',
    )
    plt.step(
        [x[0] for x in data],
        [int(x[3] or 0) / 100 for x in data],
        label='Culmulative Withdrawals',
    )

    ax.set_ylim(ymin=0)
    plt.xlabel('Date (weekly)')
    plt.ylabel('Amount ($)')
    plt.xticks(rotation=45)
    plt.legend(frameon=False)
    plt.savefig(
        fname=os.path.join(DIR, 'finances.svg'),
        bbox_inches='tight',
    )
    plt.clf()


def graph_grant_payout(grant):
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
        key=lambda x: float('inf') if x == grant else x.created.timestamp(),
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
    return graph.getvalue()


def graph_grant_distribution(grant):
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
        return (str(x)[:LIMIT - 3] + '...') if len(str(x)) > LIMIT else str(x)

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
    return graph.getvalue()


def graph_deposits_payout():
    data = [(
        distribution.models.to_step_start(x.created),
        ibis.models.Deposit.objects.filter(
            created__gte=distribution.models.to_step_start(x.created),
            created__lt=distribution.models.to_step_start(x.created,
                                                          offset=1),
            category=ibis.models.ExchangeCategory.objects.get(
                title=settings.IBIS_CATEGORY_UBP),
        ).aggregate(Max('amount'))['amount__max'],
    ) for x in distribution.models.Goal.objects.filter(
        created__gte=ibis.models.Donation.objects.order_by(
            'created').first().created).order_by('created')][1:-1]

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    plt.plot(
        [x[0] for x in data],
        [(x[1] if x[1] else 0) / 100 for x in data],
        '#84ab3f',
        label='UBP Payout',
    )

    ax.set_ylim(ymin=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.set_major_formatter(StrMethodFormatter('${x:0.0f}'))
    plt.xticks(rotation=45)
    plt.savefig(
        fname=os.path.join(DIR, 'deposit.svg'),
        bbox_inches='tight',
    )
    plt.clf()
