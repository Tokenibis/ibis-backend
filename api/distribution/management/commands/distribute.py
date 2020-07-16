import distribution.models as models

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Safely distribute UBP'

    def handle(self, *args, **options):
        models.distribute_all_safe()
