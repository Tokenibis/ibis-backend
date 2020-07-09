# upon startup: check through to make sure we've distributed
# everything that should be distributed. distribute it if not.
# Otherwise, wait until midnight on Thursday night

from django.core.management.base import BaseCommand
from django.utils.timezone import now, localtime

import distribution.models as models

STATE = {
    'UPCOMING':
    localtime(now()).replace(
        year=2019,
        month=4,
        day=5,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ),
}


class Command(BaseCommand):
    help = 'Safely distribute UBP'

    def handle(self, *args, **options):
        if STATE['UPCOMING'] < localtime(now()):
            STATE['UPCOMING'] = models.Distributor.distribute_all_safe()
