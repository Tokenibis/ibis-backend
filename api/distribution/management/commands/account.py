import distribution.models as models

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Account for investments by linking them to donations'

    def handle(self, *args, **options):
        models.refresh_accounting()
