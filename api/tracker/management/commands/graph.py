import os
import csv
import math
import ibis
import distribution
import matplotlib.pyplot as plt

from pathlib import Path
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

    def graph_control_response(self):
        data = [(
            distribution.models.to_step_start(x.created),
            x.amount,
            sum(
                y.amount for y in ibis.models.Reward.objects.filter(
                    created__gte=distribution.models.to_step_start(x.created),
                    created__lt=distribution.models.to_step_start(
                        x.created, offset=1),
                )),
            sum(
                y.amount for y in ibis.models.Donation.objects.filter(
                    created__gte=distribution.models.to_step_start(x.created),
                    created__lt=distribution.models.to_step_start(
                        x.created, offset=1),
                )),
        ) for x in distribution.models.Goal.objects.order_by('created')]

        plt.step(
            [x[0] for x in data],
            [x[1] / 100 for x in data],
            label='Donation Target',
        )

        plt.plot(
            [x[0] for x in data],
            [x[2] / 100 for x in data],
            label='Bot Rewards',
        )

        plt.plot(
            [x[0] for x in data],
            [x[3] / 100 for x in data],
            label='Actual Donations',
        )

        plt.xlabel('Date (weekly)')
        plt.ylabel('Amount ($)')
        plt.legend()
        plt.savefig(os.path.join(PATH, 'control_response.pdf'))
        plt.clf()

    def graph_organization_distribution(self):
        x_axis = [
            distribution.models.to_step_start(x.created)
            for x in distribution.models.Goal.objects.order_by('created')
        ]
        data = sorted(
            [(
                org,
                [
                    sum(
                        y.amount for y in ibis.models.Donation.objects.filter(
                            target=org,
                            created__lt=distribution.models.to_step_start(
                                x, offset=1),
                        )) / 100 for x in x_axis
                ],
            ) for org in ibis.models.Organization.objects.filter(
                is_active=True).order_by('date_joined')],
            key=lambda x: x[1][-1],
        )

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

        plt.stackplot(
            x_axis,
            *[x[1] for x in data],
            labels=[x[0] for x in data],
        )

        plt.xlabel('Date (weekly)')
        plt.ylabel('Amount ($)')

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(
            handles[-1:-8:-1],
            labels[-1:-8:-1],
            title='Line',
            loc='upper left',
        )
        plt.savefig(os.path.join(PATH, 'organization_distribution.pdf'))
        plt.clf()

    def graph_organization_edges(self):
        orgs = list(
            ibis.models.Organization.objects.filter(
                is_active=True).order_by('date_joined'))
        graph = [[0 for _ in range(len(orgs))] for _ in range(len(orgs))]
        for person in ibis.models.Person.objects.all():
            profile = [
                sum(
                    x.amount for x in ibis.models.Donation.objects.filter(
                        user=person,
                        target=org,
                    )) for org in orgs
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
