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
    def _format_body(text):
        return re.sub(r'\[(\w+)\]\((\w+)\)', r'\1 ({\2})', text.strip())

    def _format_html(text):
        return re.sub(r'\[(\w+)\]\((\w+)\)', r'<a href="{\2}">\1<\\a>',
                      text.strip())

    with open(os.path.join(DIR, 'data/email_templates.txt')) as fd:
        parts = fd.read().split('***')[1:]

    return {
        parts[i].split(':')[0]: [{
            'subject': parts[i].split(':')[1],
            'body': _format_body(x.split('===')[0]),
            'html': _format_html(x.split('===')[-1]),
        } for x in parts[i + 1].split('---')]
        for i in range(0, len(parts), 2)
    }


class Command(BaseCommand):
    help = 'Add base model objects needed for ibis app'

    def handle(self, *args, **options):

        with open(os.path.join(DIR, 'data/nonprofit_categories.json')) as fd:
            nonprofit_categories = json.load(fd)

        with open(os.path.join(DIR, 'data/deposit_categories.json')) as fd:
            deposit_categories = json.load(fd)

        for cat in sorted(nonprofit_categories.keys()):
            models.NonprofitCategory.objects.create(
                title=cat,
                description=nonprofit_categories[cat],
            )

        for cat in deposit_categories:
            models.DepositCategory.objects.create(title=cat, )

        email_templates = make_email_templates()

        for template_type, templates in email_templates.items():
            for template in templates:
                getattr(
                    notifications.models,
                    'EmailTemplate{}'.format(template_type)).objects.create(
                        subject=template['subject'],
                        body=template['body'],
                        html=template['html'],
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
