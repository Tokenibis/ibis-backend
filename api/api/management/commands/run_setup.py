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
        def _format_section(section):
            if all(x.strip()[0] == '-' for x in section.split('\n')):
                return '<ul>\n{}\n</ul>'.format('\n'.join(
                    '<li>{}</li>'.format(x.strip()[1:])
                    for x in section.split('\n')))
            else:
                return '<p>{}</p>'.format(section)

        return '\n\n'.join(
            _format_section(x) for x in re.sub(
                r'\[(\w+)\]\((\w+)\)',
                r'<a style="color: #84ab3f" href="{\2}">\1</a>',
                text.strip(),
            ).split('\n\n'))

    with open(os.path.join(DIR, 'data/email_templates.txt')) as fd:
        parts = fd.read().split('***')[1:]

    return {
        parts[i].split(':')[0]: [{
            'subject':
            parts[i].split(':')[1],
            'body':
            _format_body(x.split('===')[0]),
            'html':
            x.split('===')[1] if '===' in x else _format_html(x),
        } for x in parts[i + 1].split('---')]
        for i in range(0, len(parts), 2)
    }


class Command(BaseCommand):
    help = 'Add base model objects needed for ibis app'

    def handle(self, *args, **options):

        with open(os.path.join(DIR, 'data/organization_categories.json')) as fd:
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

        # the first organization is special; the name/info can be changed later
        models.Organization.objects.create(
            username='tokenibis',
            first_name='Token Ibis',
        )

        # the first bot is special; the name/info can be changed later
        models.Bot.objects.create(
            username='executive_bot',
            first_name='Chief Executive Bot',
        )
