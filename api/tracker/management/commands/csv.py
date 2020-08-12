import csv
import logging
import ibis.models as models

from django.db.models.fields.related import ManyToManyField, ForeignKey, OneToOneField
from django.core.management.base import BaseCommand
from api.utils import get_submodel

logger = logging.getLogger(__name__)

OMIT_LIST = [
    'id',
    'privacy_donation',
    'privacy_reward',
    'private',
    'avatar',
    'banner',
    'category',
    'image',
    'address',
    'score',
]


class Command(BaseCommand):
    help = 'Output analyzable data in both JSON and csv formats'

    def handle(self, *args, **options):
        # create user table
        # loop through user foreign keys tables to create links

        def _id(x):
            return '{}.{}'.format(x.__class__.__name__, x.id)

        def _edge(x):
            return '{}.{}'.format(get_submodel(x), x.id)

        nodes = {}
        edges = set()
        columns = set()

        for x in (list(models.User.objects.all()) + list(
                models.Entry.objects.all()) + list(
                    models.Deposit.objects.all())):
            x = get_submodel(x).objects.get(id=x.id)
            nodes[_id(x)] = {}
            for k, v in x._meta._forward_fields_map.items():
                if v.model.__module__ == 'ibis.models' and \
                   not isinstance(v, OneToOneField) and \
                   k[-3:] != '_id' and \
                   k not in OMIT_LIST:
                    if isinstance(v, ForeignKey):
                        edges.add((k, _id(x), _id(getattr(x, k))))
                    elif isinstance(v, ManyToManyField):
                        edges.update((
                            k,
                            _id(x),
                            _id(y),
                        ) for y in getattr(x, k).all())
                    else:
                        nodes[_id(x)][k] = str(getattr(x, k))
                        columns.add(k)

        # convert nodes obj into table
        header = sorted(columns)
        node_rows = [header] + [[
            nodes[x][y] if y in nodes[x] else None for y in header
        ] for x in sorted(nodes)]

        with open('nodes.csv', 'w', newline='') as fd:
            writer = csv.writer(fd)
            for row in node_rows:
                writer.writerow(row)

        with open('edges.csv', 'w', newline='') as fd:
            writer = csv.writer(fd)
            for row in sorted(edges):
                writer.writerow(row)
