import csv
import logging
import ibis.models as models

from django.db.models.fields import related
from django.core.management.base import BaseCommand
from api.utils import get_submodel

logger = logging.getLogger(__name__)

MODELS = [
    models.User,
    models.Entry,
    models.Deposit,
]

FIELDS = [
    'active',
    'amount',
    'created',
    'date',
    'date_joined',
    'description',
    'duration',
    'modified',
    'reward_min',
    'reward_range',
    'title',
]


class Command(BaseCommand):
    help = 'Output analyzable data in both JSON and csv formats'

    def handle(self, *args, **options):
        # create user table
        # loop through user foreign keys tables to create links

        def _id(x):
            return '{}.{}'.format(x.__class__.__name__.lower(), x.id)

        def _edge(x):
            return '{}.{}'.format(get_submodel(x), x.id)

        nodes = {}
        edges = set()
        columns = set()

        for x in [z for y in MODELS for z in y.objects.all()]:
            x = get_submodel(x).objects.get(id=x.id)
            nodes[_id(x)] = {}
            for k, v in x._meta._forward_fields_map.items():
                if k in FIELDS or (isinstance(v, related.RelatedField)
                                   and k[-3:] != '_id'):
                    if type(v) == related.ForeignKey:
                        if any(isinstance(getattr(x, k), z) for z in MODELS):
                            edges.add((k, _id(x), _id(getattr(x, k))))
                    elif type(v) == related.ManyToManyField:
                        edges.update((
                            k,
                            _id(x),
                            _id(y),
                        ) for y in getattr(x, k).all() if any(
                            isinstance(y, z) for z in MODELS))
                    elif not type(v) == related.OneToOneField:
                        nodes[_id(x)][k] = str(getattr(x, k))
                        columns.add(k)

        # convert nodes obj into table
        header = sorted(columns)
        node_rows = [['id'] + header] + [
            [x] + [nodes[x][y] if y in nodes[x] else None for y in header]
            for x in sorted(nodes)
        ]

        with open('nodes.csv', 'w', newline='') as fd:
            writer = csv.writer(fd)
            for row in node_rows:
                writer.writerow(row)

        with open('edges.csv', 'w', newline='') as fd:
            writer = csv.writer(fd)
            for row in [['type', 'source', 'target']] + sorted(edges):
                writer.writerow(row)
