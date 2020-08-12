#!/usr/bin/python3
#
# Generate or regenerate fake test data for the fixtures file that is
# found in ibis/fixtures/fixtures.json. Currently, this file is used
# by both scripts/reset_test.sh script and ibis/test.py.

import os
import re
import copy
import random
import json
import hashlib

from api.management.commands.run_setup import make_email_templates

from django.utils.timezone import now, timedelta

from django.core.management.base import BaseCommand

DIR = os.path.dirname(os.path.realpath(__file__))

BIRDS = 'https://s3.us-east-2.amazonaws.com/app.tokenibis.org/birds/{}.jpg'
BIRDS_LEN = 233

BOTS = 'https://s3.us-east-2.amazonaws.com/app.tokenibis.org/bots/{}.png'
BOTS_LEN = 512

WINDOW = 365 * 24 * 60 * 60 - 3


class Markov(object):
    def __init__(self, corpus):
        self.cache = {}
        self.words = []
        for filename in os.listdir(corpus):
            self.words.extend(self.file_to_words(corpus + '/' + filename))
        self.word_size = len(self.words)
        self.database()

    def file_to_words(self, filepath):
        with open(filepath) as fd:
            data = fd.read()
        cleaned = re.sub(r'W+', '', data)
        words = cleaned.split()
        return words

    def triples(self):
        """Generates triples from the given data string. So if our string were
        "What a lovely day", we'd generate (What, a, lovely) and then (a,
        lovely, day).

        """

        if len(self.words) < 3:
            return

        for i in range(len(self.words) - 2):
            yield (self.words[i], self.words[i + 1], self.words[i + 2])

        # add dummy wrap around to avoid end of document corner case
        yield (
            self.words[len(self.words) - 2],
            self.words[len(self.words) - 1],
            self.words[0],
        )
        yield (
            self.words[len(self.words) - 1],
            self.words[0],
            self.words[1],
        )

    def database(self):
        for w1, w2, w3 in self.triples():
            key = (w1, w2)
            if key in self.cache:
                self.cache[key].append(w3)
            else:
                self.cache[key] = [w3]

    def generate_markov_text(self, size=30):
        seed = random.randint(0, self.word_size - 3)
        seed_word, next_word = self.words[seed], self.words[seed + 1]
        w1, w2 = seed_word, next_word
        gen_words = []
        for i in range(size):
            gen_words.append(w1)
            w1, w2 = w2, random.choice(self.cache[(w1, w2)])
        gen_words.append(w2)
        text = ' '.join(gen_words)
        return text[0].capitalize() + text[1:].rsplit('.', 1)[0] + '.'


class Model:
    def __init__(self):
        self.organization_categories = []
        self.exchange_categories = []
        self.email_templates = []
        self.donation_messages = []
        self.users = []
        self.general_users = []
        self.bots = []
        self.people = []
        self.organizations = []
        self.deposits = []
        self.withdrawals = []
        self.entries = []
        self.donations = []
        self.rewards = []
        self.news = []
        self.events = []
        self.posts = []
        self.activities = []
        self.comments = []

        with open(os.path.join(DIR, '../../../../config.json')) as fd:
            app = json.load(fd)['social']

        self.sites = [{
            'model': 'sites.Site',
            'pk': 1,
            'fields': {
                'domain': '127.0.0.1',
            }
        }]

        self.socialApplications = [
            {
                'model': 'socialaccount.SocialApp',
                'pk': 1,
                'fields': {
                    'name': 'facebook',
                    'provider': 'facebook',
                    'client_id': app['facebook']['client_id'],
                    'secret': app['facebook']['secret_key'],
                    'sites': [1],
                }
            },
            {
                'model': 'socialaccount.SocialApp',
                'pk': 2,
                'fields': {
                    'name': 'google',
                    'provider': 'google',
                    'client_id': app['google']['client_id'],
                    'secret': app['google']['secret_key'],
                    'sites': [1],
                }
            },
        ]

        self.now = now()

    def _random_time(self):
        return self.now - timedelta(seconds=random.randint(0, WINDOW))

    def add_organization_category(self, title, description):
        pk = len(self.organization_categories) + 1

        self.organization_categories.append({
            'model': 'ibis.OrganizationCategory',
            'pk': pk,
            'fields': {
                'title': title,
                'description': description,
            },
        })

        return pk

    def add_exchange_category(self, title):
        pk = len(self.exchange_categories) + 1

        self.exchange_categories.append({
            'model': 'ibis.ExchangeCategory',
            'pk': pk,
            'fields': {
                'title': title,
            },
        })

        return pk

    def add_email_template(self, template_type, subject, body, html):
        pk = len(self.email_templates) + 1

        self.email_templates.append({
            'model':
            'notifications.EmailTemplate{}'.format(template_type),
            'pk':
            pk,
            'fields': {
                'subject': subject,
                'body': body,
                'html': html,
            }
        })

    def add_donation_message(self, description):
        pk = len(self.donation_messages) + 1

        self.donation_messages.append({
            'model': 'notifications.DonationMessage',
            'pk': pk,
            'fields': {
                'description': description,
            },
        })

    def add_organization(
            self,
            name,
            description,
            category,
            score,
            date_joined=None,
    ):
        pk = len(self.general_users) + 1

        unique_name = re.sub(r'\W+', '_', name).lower()[:15]
        i = 0
        while unique_name in [
                x['fields']['first_name'] for x in self.general_users
        ]:
            i += 1
            suffix = '_{}'.format(i)
            unique_name = unique_name[:15 - len(suffix)] + suffix

        self.general_users.append({
            'model': 'users.GeneralUser',
            'pk': pk,
            'fields': {
                'username': unique_name,
                'first_name': unique_name,
                'email': '{}@example.com'.format(unique_name),
                'date_joined':
                date_joined if date_joined else self._random_time(),
            }
        })

        self.users.append({
            'model': 'ibis.User',
            'pk': pk,
            'fields': {
                'avatar': BIRDS.format(hash(name) % BIRDS_LEN),
                'description': description,
                'score': score,
                'following': [],
            },
        })

        self.organizations.append({
            'model': 'ibis.Organization',
            'pk': pk,
            'fields': {
                'category': category,
                'banner': BIRDS.format(hash(name + '_') % BIRDS_LEN),
                'link': 'https://{}.org'.format(unique_name.replace(' ', '_')),
            }
        })

        return pk

    def add_donation(
            self,
            source,
            target,
            amount,
            description,
            score,
            created=None,
    ):
        assert target in [x['pk'] for x in self.organizations]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'description': description,
                'like': [],
                'created': created if created else self._random_time(),
            }
        })
        self.donations.append({
            'model': 'ibis.Donation',
            'pk': pk,
            'fields': {
                'user': source,
                'target': target,
                'amount': amount,
                'score': score,
            }
        })

        return pk

    def add_person(self, first, last, description, score, date_joined=None):
        pk = len(self.general_users) + 1
        username = '{}_{}_{}'.format(pk, first, last)[:15].lower()

        self.general_users.append({
            'model': 'users.GeneralUser',
            'pk': pk,
            'fields': {
                'username': username,
                'first_name': first,
                'last_name': last,
                'email': '{}@example.com'.format(username),
                'date_joined':
                date_joined if date_joined else self._random_time(),
            }
        })

        self.users.append({
            'model': 'ibis.User',
            'pk': pk,
            'fields': {
                'following': [],
                'avatar': BIRDS.format(hash(first + ' ' + last) % BIRDS_LEN),
                'description': description,
                'score': score,
            }
        })

        self.people.append({
            'model': 'ibis.Person',
            'pk': pk,
            'fields': {},
        })

        return pk

    def add_bot(self, name, description, score, date_joined=None):
        pk = len(self.general_users) + 1
        username = '{}_{}'.format(pk, name)[:15].lower().replace(' ', '_')

        self.general_users.append({
            'model': 'users.GeneralUser',
            'pk': pk,
            'fields': {
                'username': username,
                'first_name': name,
                'email': '{}@example.com'.format(username),
                'date_joined':
                date_joined if date_joined else self._random_time(),
            }
        })

        self.users.append({
            'model': 'ibis.User',
            'pk': pk,
            'fields': {
                'following': [],
                'avatar': BOTS.format(hash(name) % BOTS_LEN),
                'description': description,
                'score': score,
            }
        })

        self.bots.append({
            'model': 'ibis.Bot',
            'pk': pk,
            'fields': {},
        })

        return pk

    def add_reward(self,
                   source,
                   target,
                   amount,
                   description,
                   score,
                   activity=None):
        assert target not in [x['pk'] for x in self.organizations]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'description': description,
                'like': [],
                'created': self._random_time(),
            }
        })

        self.rewards.append({
            'model': 'ibis.Reward',
            'pk': pk,
            'fields': {
                'user': source,
                'target': target,
                'amount': amount,
                'score': score,
                'related_activity': activity,
            }
        })

        return pk

    def add_news(self, organization, title, description, score):
        assert organization in [x['pk'] for x in self.organizations]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'description': description,
                'like': [],
                'created': self._random_time(),
            }
        })

        self.news.append({
            'model': 'ibis.News',
            'pk': pk,
            'fields': {
                'user': organization,
                'title': title,
                'bookmark': [],
                'link': 'https://{}.org'.format(title.replace(' ', '_')),
                'image': BIRDS.format(hash(title) % BIRDS_LEN),
                'score': score,
            }
        })

        return pk

    def add_event(
            self,
            organization,
            title,
            description,
            date,
            duration,
            address,
            score,
    ):
        assert organization in [x['pk'] for x in self.organizations]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'description': description,
                'like': [],
                'created': self._random_time(),
            }
        })

        self.events.append({
            'model': 'ibis.Event',
            'pk': pk,
            'fields': {
                'user': organization,
                'title': title,
                'link': 'https://{}.org'.format(title.replace(' ', '_')),
                'image': BIRDS.format(hash(title) % BIRDS_LEN),
                'rsvp': [],
                'date': date,
                'duration': duration,
                'address': address,
                'score': score,
            }
        })

        return pk

    def add_post(self, user, title, description, score):
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'description': description,
                'like': [],
                'created': self._random_time(),
            }
        })

        self.posts.append({
            'model': 'ibis.Post',
            'pk': pk,
            'fields': {
                'user': user,
                'title': title,
                'score': score,
                'bookmark': [],
            }
        })

        return pk

    def add_activity(
            self,
            user,
            title,
            description,
            active,
            reward_min,
            reward_range,
            score,
    ):
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'description': description,
                'like': [],
                'created': self._random_time(),
            }
        })

        self.activities.append({
            'model': 'ibis.Activity',
            'pk': pk,
            'fields': {
                'user': user,
                'title': title,
                'active': active,
                'reward_min': reward_min,
                'reward_range': reward_range,
                'score': score,
                'bookmark': [],
            }
        })

        return pk

    def add_comment(self, user, parent, description, score):
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'description':
                description,
                'like': [],
                'created':
                max(self._random_time(), [
                    x['fields']['created'] for x in self.entries
                    if x['pk'] == parent
                ][0])
            }
        })

        self.comments.append({
            'model': 'ibis.Comment',
            'pk': pk,
            'fields': {
                'user': user,
                'parent': parent,
                'score': score,
            }
        })

        return pk

    def add_deposit(self, user, amount, category, created=None):
        pk = len(self.deposits) + 1

        sha = hashlib.sha256()
        sha.update(str(pk).encode())
        description = '{}'.format(sha.hexdigest())

        self.deposits.append({
            'model': 'ibis.Deposit',
            'pk': pk,
            'fields': {
                'user': user,
                'description': description,
                'amount': amount,
                'category': category,
                'created': created if created else self._random_time(),
            }
        })

        return pk

    def add_withdrawal(self, user, amount, category, created=None):
        pk = len(self.withdrawals) + 1

        self.deposits.append({
            'model': 'ibis.Withdrawal',
            'pk': pk,
            'fields': {
                'user': user,
                'amount': amount,
                'created': self._random_time(),
                'category': category,
                'created': created if created else self._random_time(),
            }
        })

        return pk

    def add_follow(self, source, target):
        user = next((x for x in self.users if x['pk'] == source), None)
        following = user['fields']['following']
        if target not in following:
            following.append(target)

    def add_rsvp(self, person, event):
        event_obj = next((x for x in self.events if x['pk'] == event), None)
        event_obj['fields']['rsvp'].append(person)

    def add_bookmark(self, person, entry):
        bookmarkable = self.news + self.posts
        entry_obj = next((x for x in bookmarkable if x['pk'] == entry), None)
        entry_obj['fields']['bookmark'].append(person)

    def add_like(self, person, entry):
        entry_obj = next((x for x in self.entries if x['pk'] == entry), None)
        entry_obj['fields']['like'].append(person)

    def get_model(self):
        serializable_entries = copy.deepcopy(self.entries)
        for x in serializable_entries:
            x['fields']['created'] = str(x['fields']['created'])

        serializable_deposits = copy.deepcopy(self.deposits)
        for x in serializable_deposits:
            x['fields']['created'] = str(x['fields']['created'])

        serializable_users = copy.deepcopy(self.general_users)
        for x in serializable_users:
            x['fields']['date_joined'] = str(x['fields']['date_joined'])

        partial_users = copy.deepcopy(self.users)
        for x in partial_users:
            del x['fields']['following']

        partial_entries = copy.deepcopy(serializable_entries)
        for x in partial_entries:
            x['fields']['like'] = []

        return [
            serializable_users,
            partial_users,
            self.organization_categories,
            self.exchange_categories,
            self.email_templates,
            self.donation_messages,
            self.organizations,
            self.people,
            self.bots,
            self.users,
            serializable_deposits,
            partial_entries,
            self.donations,
            self.activities,
            self.rewards,
            self.news,
            self.events,
            self.posts,
            self.comments,
            serializable_entries,
            self.sites,
            self.socialApplications,
        ]


class Command(BaseCommand):
    help = 'Generate/regenerate fixture.json file in ibis/fixtures'

    def add_arguments(self, parser):
        parser.add_argument('--num_bot', type=int, required=True)
        parser.add_argument('--num_person', type=int, required=True)
        parser.add_argument('--num_organization', type=int, required=True)
        parser.add_argument('--num_deposit', type=int, required=True)
        parser.add_argument('--num_withdrawal', type=int, required=True)
        parser.add_argument('--num_donation', type=int, required=True)
        parser.add_argument('--num_reward', type=int, required=True)
        parser.add_argument('--num_news', type=int, required=True)
        parser.add_argument('--num_event', type=int, required=True)
        parser.add_argument('--num_post', type=int, required=True)
        parser.add_argument('--num_activity', type=int, required=True)
        parser.add_argument('--num_comment', type=int, required=True)
        parser.add_argument('--num_follow', type=int, required=True)
        parser.add_argument('--num_rsvp', type=int, required=True)
        parser.add_argument('--num_bookmark', type=int, required=True)
        parser.add_argument('--num_like', type=int, required=True)

    def handle(self, *args, **options):
        self.run(
            num_bot=options['num_bot'],
            num_person=options['num_person'],
            num_organization=options['num_organization'],
            num_deposit=options['num_deposit'],
            num_withdrawal=options['num_withdrawal'],
            num_donation=options['num_donation'],
            num_reward=options['num_reward'],
            num_news=options['num_news'],
            num_event=options['num_event'],
            num_post=options['num_post'],
            num_activity=options['num_activity'],
            num_comment=options['num_comment'],
            num_follow=options['num_follow'],
            num_rsvp=options['num_rsvp'],
            num_bookmark=options['num_bookmark'],
            num_like=options['num_like'],
        )

    def run(
            self,
            num_bot,
            num_person,
            num_organization,
            num_deposit,
            num_withdrawal,
            num_donation,
            num_reward,
            num_news,
            num_event,
            num_post,
            num_activity,
            num_comment,
            num_follow,
            num_rsvp,
            num_bookmark,
            num_like,
    ):
        assert num_deposit >= num_person

        random.seed(0)
        model = Model()

        # load data
        markov = Markov(os.path.join(DIR, 'data/corpus'))

        with open(os.path.join(DIR,
                               'data/organization_categories.json')) as fd:
            np_cat_raw = json.load(fd)

        with open(os.path.join(DIR, 'data/exchange_categories.json')) as fd:
            dp_cat_raw = json.load(fd)

        email_templates = make_email_templates()

        with open(os.path.join(DIR, 'data/organizations.json')) as fd:
            np_raw = sorted(json.load(fd), key=lambda x: x['name'])

        with open(os.path.join(DIR, 'data/names.txt')) as fd:
            people_raw = [x.strip().split(' ') for x in fd.readlines()]

        with open(os.path.join(DIR, 'data/nouns.txt')) as fd:
            nouns = [x[0].capitalize() + x[1:].strip() for x in fd.readlines()]

        with open(os.path.join(DIR, 'data/verbs.txt')) as fd:
            verbs = [x[0].capitalize() + x[1:].strip() for x in fd.readlines()]

        with open(os.path.join(DIR, 'data/adjectives.txt')) as fd:
            adjectives = [
                x[0].capitalize() + x[1:].strip() for x in fd.readlines()
            ]

        event_type = [
            'Gala',
            'Extravaganza',
            'Bash',
            'Party',
            'Ceremony',
            'Experience',
            'Diner',
            'Carnival',
            'Tournament',
            'Funfest',
            'Festival',
            'Invitational',
        ]

        with open(os.path.join(DIR, 'data/addresses.json')) as fd:
            addresses = json.load(fd)

        # make organization categories from charity navigator categories
        organization_categories = [
            model.add_organization_category(x, np_cat_raw[x])
            for x in np_cat_raw
        ]

        # make deposit categories from charity navigator categories
        exchange_categories = [
            model.add_exchange_category(x) for x in dp_cat_raw
        ]

        for template_type, templates in email_templates.items():
            for template in templates:
                model.add_email_template(
                    template_type,
                    template['subject'],
                    template['body'],
                    template['html'],
                )

        # add donation messages
        with open(os.path.join(DIR, 'data/donation_messages.json')) as fd:
            for x in json.load(fd):
                model.add_donation_message(x)

        # add special first organization
        model.add_organization(
            'Token Ibis',
            'First organization',
            random.choice(organization_categories),
            random.randint(0, 100),
        )

        # make organizations from scraped list of real organizations
        organizations = [
            model.add_organization(
                x['name'],
                x['description'],
                random.choice(organization_categories),
                random.randint(0, 100),
            ) for x in np_raw[:num_organization - 1]
        ]

        # make people
        people_raw = people_raw * (int((num_person - 1) / len(people_raw)) + 1)
        people = [
            model.add_person(
                x[0],
                x[1],
                markov.generate_markov_text(size=200),
                random.randint(0, 100),
            ) for x in people_raw[:num_person]
        ]

        # make bots
        bots = [
            model.add_bot(
                '{} Bot'.format(x),
                markov.generate_markov_text(size=200),
                random.randint(0, 100),
            ) for x in random.sample(nouns, num_bot)
        ]

        # make deposit money for all people
        for person in people:
            model.add_deposit(
                person,
                1000000,
                random.choice(exchange_categories),
                created=model.now - timedelta(seconds=WINDOW + 2),
            )

        # make deposit money for all bots
        for bot in bots:
            model.add_deposit(
                bot,
                1000000,
                random.choice(exchange_categories),
                created=model.now - timedelta(seconds=WINDOW + 2),
            )

        # initial donations for organizations
        for organization in organizations:
            donor = random.choice(people)
            model.add_deposit(
                donor,
                1000000,
                random.choice(exchange_categories),
                created=model.now - timedelta(seconds=WINDOW + 2),
            )
            model.add_donation(
                donor,
                organization,
                1000000,
                'initial',
                0,
                created=model.now - timedelta(seconds=WINDOW + 1),
            )

        # make random deposits
        for i in range(num_deposit -
                       (num_person + num_organization + num_bot)):
            model.add_deposit(
                random.choice(people),
                random.randint(1, 10000),
                random.choice(exchange_categories),
            )

        # make random donations
        donations = []
        for i in range(num_donation - len(organizations)):
            donations.append(
                model.add_donation(
                    random.choice(people),
                    random.choice(organizations),
                    random.randint(1, 10000),
                    markov.generate_markov_text(),
                    random.randint(0, 100),
                ))

        # make fake news
        news = []
        for i in range(num_news):
            title = 'Breaking: {} {}s {}'.format(
                random.choice(nouns),
                random.choice(verbs),
                random.choice(nouns),
            )
            raw = markov.generate_markov_text(size=600).strip()
            sentences = raw.split('.')
            sentences[0] = '[{}](https://tokenibis.org)\n'.format(sentences[0])
            sentences.insert(
                round(len(sentences) * 0.25), '\n# {}\n'.format(
                    markov.generate_markov_text(size=3)))
            sentences.insert(
                round(len(sentences) * 0.5), '\n# {}\n'.format(
                    markov.generate_markov_text(size=3)))
            for i in range(2, 5):
                sentences[-i] = '\n* {}\n'.format(sentences[-i])
            description = '.'.join(sentences)
            news.append(
                model.add_news(
                    random.choice(organizations),
                    title,
                    description,
                    random.randint(0, 100),
                ))

        # make fake events
        events = []
        date_next = now()
        for i in range(num_event):
            title = 'The {} {} {}'.format(
                random.choice(adjectives),
                random.choice(nouns),
                random.choice(event_type),
            )
            date_next += timedelta(hours=random.randint(0, 48))
            address = random.choice(addresses)
            events.append(
                model.add_event(
                    random.choice(organizations),
                    title,
                    markov.generate_markov_text(size=60),
                    date_next.strftime('%Y-%m-%dT%H:%M:%S+00:00'),
                    60,
                    address,
                    random.randint(0, 100),
                ))

        # make fake posts
        posts = []
        for i in range(num_post):
            title = 'How can I {} a {} with {}?'.format(
                random.choice(verbs).lower(),
                random.choice(nouns).lower(),
                random.choice(nouns).lower(),
            )
            description = markov.generate_markov_text(size=200)
            posts.append(
                model.add_post(
                    random.choice(people),
                    title,
                    description,
                    random.randint(0, 100),
                ))

        # make fake activities
        activity = []
        for i in range(num_activity):
            title = 'Offering reward to {} a {}'.format(
                random.choice(verbs).lower(),
                random.choice(nouns).lower(),
            )
            description = markov.generate_markov_text(size=200)
            activity.append(
                model.add_activity(
                    random.choice(bots),
                    title,
                    description,
                    random.choice([True, False]),
                    random.randint(0, 1000),
                    random.randint(0, 1000),
                    random.randint(0, 100),
                ))

        # make random rewards
        rewards = []
        for i in range(num_reward):
            rewards.append(
                model.add_reward(
                    random.choice(bots),
                    random.choice(people),
                    random.randint(1, 10000),
                    markov.generate_markov_text(),
                    random.randint(0, 100),
                    random.choice(activity),
                ))

        # make fake comments
        comments = []
        for i in range(num_comment):
            commentable = rewards + donations + news + events + posts\
                + comments
            parent = random.choice(commentable)
            description = markov.generate_markov_text(
                size=random.randint(25, 100))
            comments.append(
                model.add_comment(
                    random.choice(people + organizations),
                    parent,
                    description,
                    random.randint(0, 100),
                ))

        # add followers
        for i in range(num_follow):
            source, target = random.sample(people + organizations, 2)
            model.add_follow(source, target)

        # add rsvps
        for i in range(num_rsvp):
            model.add_rsvp(
                random.choice(people + organizations),
                random.choice(events),
            )

        # add bookmarks
        for i in range(num_bookmark):
            model.add_bookmark(
                random.choice(people + organizations),
                random.choice(news + posts))

        # add likes
        likeable = rewards + donations + news + events + posts + comments
        for i in range(num_like):
            model.add_like(
                random.choice(people + organizations),
                random.choice(likeable),
            )

        # save fixtures
        fixtures_dir = os.path.join(DIR, '../../fixtures')
        if not os.path.exists(fixtures_dir):
            os.makedirs(fixtures_dir)

        fixtures = model.get_model()
        for i, fixture in enumerate(fixtures):
            with open(
                    os.path.join(
                        fixtures_dir, '{number:0{width}d}.json'.format(
                            width=len(str(len(fixtures))), number=i)),
                    'w') as fd:
                json.dump(fixture, fd, indent=2)
