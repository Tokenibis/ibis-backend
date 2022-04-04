import distribution.network as network

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Account for grants by linking them to donations'

    def handle(self, *args, **options):
        network.run()
