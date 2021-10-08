import os
import csv
import math
import ibis
import random
import distribution
import matplotlib.pyplot as plt

from pathlib import Path
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.core.management.base import BaseCommand

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(DIR, '..', '..', 'graphs')

plt.style.use('dark_background')


class Command(BaseCommand):
    help = 'Output ibis model graphs'

    def handle(self, *args, **options):
        Path(PATH).mkdir(parents=True, exist_ok=True)
        self.graph_control_response()
        self.graph_organization_distribution()
        self.graph_organization_edges()
        self.graph_users_time()
        self.graph_organization_engagement()
        self.graph_finances_time()

    def graph_control_response(self):
        data = [(
            distribution.models.to_step_start(x.created),
            x.amount(),
            ibis.models.Donation.objects.filter(
                created__gte=distribution.models.to_step_start(x.created),
                created__lt=distribution.models.to_step_start(
                    x.created, offset=1),
            ).aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
        ) for x in distribution.models.Goal.objects.order_by('created')][1:-1]

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

        plt.step(
            [x[0] for x in data],
            [x[1] / 100 for x in data],
            label='Target Donations',
        )

        plt.plot(
            [x[0] for x in data],
            [x[2] / 100 for x in data],
            label='Actual Donations',
        )

        ax.set_ylim(ymin=0)
        plt.xlabel('Date (weekly)')
        plt.ylabel('Amount ($)')
        plt.xticks(rotation=45)
        plt.legend()
        plt.savefig(
            os.path.join(PATH, 'control_response.pdf'),
            bbox_inches='tight',
        )
        plt.clf()

    def graph_organization_distribution(self):
        x_axis = [
            distribution.models.to_step_start(x.created)
            for x in distribution.models.Goal.objects.filter(
                created__gte=ibis.models.Donation.objects.order_by(
                    'created').first().created).order_by('created')
        ][:-1]
        data = sorted(
            [(
                org,
                [
                    ibis.models.Donation.objects.filter(
                        target=org,
                        created__lt=distribution.models.to_step_start(
                            x, offset=1),
                    ).aggregate(amount=Coalesce(Sum('amount'), 0))['amount'] /
                    100 for x in x_axis
                ],
            ) for org in ibis.models.Organization.objects.filter(
                is_active=True).order_by('date_joined')],
            key=lambda x: x[1][-1],
        )

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

        random.seed(0)

        plt.stackplot(
            x_axis,
            *[x[1] for x in data],
            labels=[x[0] for x in data],
            colors=[
                '#%02X%02X%02X' % (
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                ) for _ in data
            ])

        plt.xlabel('Date (weekly)')
        plt.ylabel('Amount ($)')

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(
            handles[-1:-13:-1],
            labels[-1:-13:-1],
            loc='upper left',
            fontsize=8,
        )
        plt.xticks(rotation=45)
        plt.savefig(
            os.path.join(PATH, 'organization_distribution.pdf'),
            bbox_inches='tight',
        )
        plt.clf()

    def graph_organization_edges(self):
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

        with open(
                os.path.join(
                    PATH,
                    'organization_edges.csv',
                ), 'w', newline='') as fd:
            writer = csv.writer(fd)
            writer.writerow([''] + [str(x) for x in orgs])
            for i, line in enumerate(graph):
                writer.writerow([str(orgs[i])] + line)

    def graph_users_time(self):
        data = [(
            distribution.models.to_step_start(x.created),
            len(
                set(
                    y.user for y in ibis.models.Donation.objects.filter(
                        created__gte=distribution.models.to_step_start(
                            x.created),
                        created__lt=distribution.models.to_step_start(
                            x.created, offset=1),
                    ))),
            len(
                set(
                    y for y in ibis.models.Person.objects.filter(
                        is_active=True,
                        date_joined__lt=distribution.models.to_step_start(
                            x.created, offset=1))
                    if ibis.models.Donation.objects.filter(user=y).exists())),
        ) for x in distribution.models.Goal.objects.filter(
                created__gte=ibis.models.Donation.objects.order_by(
                    'created').first().created).order_by('created')][:-1]

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

        plt.plot(
            [x[0] for x in data],
            [x[1] for x in data],
            label='Active Users (Weekly)',
        )
        plt.plot(
            [x[0] for x in data],
            [x[2] for x in data],
            label='Total Users (Culmulative)',
        )

        ax.set_ylim(ymin=0)
        plt.xlabel('Date (weekly)')
        plt.ylabel('Number of Users')
        plt.xticks(rotation=45)
        plt.legend()
        plt.savefig(
            os.path.join(PATH, 'users_time.pdf'),
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
                amount = sum(
                    x.amount for x in org.donation_set.filter(
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
                elif org.comment_set.filter(
                        created__gte=a, created__lt=b).exists():
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
        plt.savefig(os.path.join(PATH, 'organization_engagement.pdf'))
        plt.clf()

    def graph_finances_time(self):
        data = [(
            x,
            ibis.models.Grant.objects.filter(
                created__lt=distribution.models.to_step_start(x, offset=1)
            ).aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
            ibis.models.Donation.objects.filter(
                created__lt=distribution.models.to_step_start(x, offset=1)
            ).aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
            ibis.models.Withdrawal.objects.filter(
                created__lt=distribution.models.to_step_start(x, offset=1)).
            aggregate(amount=Coalesce(Sum('amount'), 0))['amount'],
        ) for x in [
            distribution.models.to_step_start(
                ibis.models.Donation.objects.order_by(
                    'created').first().created,
                offset=i,
            ) for i in range(
                int((ibis.models.Donation.objects.order_by('created').last().
                     created - ibis.models.Donation.objects.order_by(
                         'created').first().created).days / 7))
        ]]

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

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
        plt.ylabel('Dollars ($)')
        plt.xticks(rotation=45)
        plt.legend()
        plt.savefig(
            os.path.join(PATH, 'finance_time.pdf'),
            bbox_inches='tight',
        )
        plt.clf()
