import os
import re
import json

from django.core.management.base import BaseCommand

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
import ibis.models as models
import notifications.models

DIR = os.path.dirname(os.path.realpath(__file__))


def make_email_templates():
    with open(os.path.join(DIR, 'data/email_templates.txt')) as fd:
        parts = fd.read().split('***')[1:]

    return {
        parts[i].split(':')[0]: [{
            'subject': parts[i].split(':')[1],
            'body': x,
        } for x in parts[i + 1].split('---')]
        for i in range(0, len(parts), 2)
    }


class Command(BaseCommand):
    help = 'Add base model objects needed for ibis app'

    def handle(self, *args, **options):

        with open(os.path.join(DIR,
                               'data/organization_categories.json')) as fd:
            organization_categories = json.load(fd)

        with open(os.path.join(DIR, 'data/exchange_categories.json')) as fd:
            exchange_categories = json.load(fd)

        with open(os.path.join(DIR, 'data/donation_messages.json')) as fd:
            donation_messages = json.load(fd)

        for cat in sorted(organization_categories.keys()):
            models.OrganizationCategory.objects.create(
                title=cat,
                description=organization_categories[cat],
            )

        for cat in exchange_categories:
            models.ExchangeCategory.objects.create(title=cat, )

        for message in donation_messages:
            notifications.models.DonationMessage.objects.create(
                description=message)

        email_templates = make_email_templates()

        for template_type, templates in email_templates.items():
            for template in templates:
                getattr(
                    notifications.models,
                    'EmailTemplate{}'.format(template_type)).objects.create(
                        subject=template['subject'],
                        body=template['body'],
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
