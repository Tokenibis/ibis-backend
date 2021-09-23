import json

import distribution.models as models

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Account for investments by linking them to donations'

    def handle(self, *args, **options):

        with open('accounting.json', 'w') as fd:
            json.dump(
                [{
                    'investment': {
                        'name': x.name,
                        'start': str(models.to_step_start(x.start)),
                        'end': str(models.to_step_start(x.end)),
                        'description': x.description,
                    },
                    'donations': [{
                        'source': str(y.user),
                        'target': str(y.target),
                        'created': str(y.created),
                        'amount': a,
                        'description': y.description,
                        'replies': []
                    } for y, a in donations.items()]
                } for x, donations in
                 models.Investment.account_investments().items()],
                fd,
                indent=2,
            )
