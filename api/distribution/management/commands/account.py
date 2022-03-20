import distribution.models as models
import distribution.circles as circles
import distribution.graph as graph

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Account for grants by linking them to donations'

    def handle(self, *args, **options):
        models.refresh_accounting()
        circles.run()
        graph.run()
