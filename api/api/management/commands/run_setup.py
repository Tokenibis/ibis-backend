import os
import json

from django.core.management.base import BaseCommand

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import ibis.models as models

DIR = os.path.dirname(os.path.realpath(__file__))


class Command(BaseCommand):
    help = 'Add base model objects needed for ibis app'

    def handle(self, *args, **options):

        with open(os.path.join(DIR, 'data/nonprofit_categories.json')) as fd:
            nonprofit_categories = json.load(fd)

        with open(os.path.join(DIR, 'data/nonprofit_categories.json')) as fd:
            deposit_categories = json.load(fd)

        for cat in sorted(nonprofit_categories.keys()):
            models.NonprofitCategory.objects.create(
                title=cat,
                description=nonprofit_categories[cat],
            )

        for cat in deposit_categories:
            models.DepositCategory.objects.create(
                title=cat,
            )

        with open(os.path.join(DIR, '../../../../config.json')) as fd:
            config = json.load(fd)

        site = Site.objects.all().first()

        app = SocialApp.objects.create(
            name='facebook',
            provider='facebook',
            client_id=config['social']['facebook']['client_id'],
            secret=config['social']['facebook']['secret_key'],
        )
        app.sites.add(site)

        app = SocialApp.objects.create(
            name='google',
            provider='google',
            client_id=config['social']['google']['client_id'],
            secret=config['social']['google']['secret_key'],
        )
        app.sites.add(site)
        app.save()

