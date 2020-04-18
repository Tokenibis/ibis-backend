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

from django.utils.timezone import now, timedelta

from django.core.management.base import BaseCommand

DIR = os.path.dirname(os.path.realpath(__file__))

BIRDS = 'https://s3.us-east-2.amazonaws.com/app.tokenibis.org/birds/{}.jpg'
BIRDS_LEN = 233


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
        self.nonprofit_categories = []
        self.ibisUsers = []
        self.users = []
        self.people = []
        self.nonprofits = []
        self.deposits = []
        self.entries = []
        self.donations = []
        self.transactions = []
        self.news = []
        self.events = []
        self.posts = []
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

    def add_nonprofit_category(self, title, description):
        pk = len(self.nonprofit_categories) + 1

        self.nonprofit_categories.append({
            'model': 'ibis.NonProfitCategory',
            'pk': pk,
            'fields': {
                'title': title,
                'description': description,
            },
        })

        return pk

    def add_nonprofit(self, name, description, category, score):
        pk = len(self.users) + 1

        unique_name = re.sub(r'\W+', '_', name).lower()[:15]
        i = 0
        while unique_name in [x['fields']['last_name'] for x in self.users]:
            i += 1
            suffix = '_{}'.format(i)
            unique_name = unique_name[:15 - len(suffix)] + suffix

        self.users.append({
            'model': 'users.User',
            'pk': pk,
            'fields': {
                'username': unique_name,
                'first_name': '',
                'last_name': unique_name,
                'email': '{}@example.com'.format(unique_name),
            }
        })

        self.ibisUsers.append({
            'model': 'ibis.IbisUser',
            'pk': pk,
            'fields': {
                'avatar': BIRDS.format(hash(name) % BIRDS_LEN),
                'score': score,
                'following': [],
            },
        })

        self.nonprofits.append({
            'model': 'ibis.Nonprofit',
            'pk': pk,
            'fields': {
                'category': category,
                'description': description,
                'banner': BIRDS.format(hash(name + '_') % BIRDS_LEN),
                'link': 'https://{}.org'.format(unique_name.replace(' ', '_')),
            }
        })

        return pk

    def add_donation(self, source, target, amount, description, score):
        assert target in [x['pk'] for x in self.nonprofits]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'user': source,
                'description': description,
                'like': [],
            }
        })
        self.donations.append({
            'model': 'ibis.Donation',
            'pk': pk,
            'fields': {
                'target': target,
                'amount': amount,
                'score': score,
            }
        })

        return pk

    def add_person(self, first, last, score):
        pk = len(self.users) + 1
        username = '{}_{}_{}'.format(pk, first, last)[:15].lower()

        self.users.append({
            'model': 'users.User',
            'pk': pk,
            'fields': {
                'username': username,
                'first_name': first,
                'last_name': last,
                'email': '{}@example.com'.format(username),
            }
        })

        self.ibisUsers.append({
            'model': 'ibis.IbisUser',
            'pk': pk,
            'fields': {
                'following': [],
                'avatar': BIRDS.format(hash(first + ' ' + last) % BIRDS_LEN),
                'score': score,
            }
        })

        self.people.append({
            'model': 'ibis.Person',
            'pk': pk,
            'fields': {},
        })

        return pk

    def add_transaction(
            self,
            source,
            target,
            amount,
            description,
            score,
    ):
        assert target not in [x['pk'] for x in self.nonprofits]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'user': source,
                'description': description,
                'like': [],
            }
        })

        self.transactions.append({
            'model': 'ibis.Transaction',
            'pk': pk,
            'fields': {
                'target': target,
                'amount': amount,
                'score': score,
            }
        })

        return pk

    def add_news(self, nonprofit, title, description, score):
        assert nonprofit in [x['pk'] for x in self.nonprofits]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'user': nonprofit,
                'description': description,
                'like': [],
            }
        })

        self.news.append({
            'model': 'ibis.News',
            'pk': pk,
            'fields': {
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
            nonprofit,
            title,
            description,
            date,
            duration,
            address,
            score,
    ):
        assert nonprofit in [x['pk'] for x in self.nonprofits]
        pk = len(self.entries) + 1

        self.entries.append({
            'model': 'ibis.Entry',
            'pk': pk,
            'fields': {
                'user': nonprofit,
                'description': description,
                'like': [],
            }
        })

        self.events.append({
            'model': 'ibis.Event',
            'pk': pk,
            'fields': {
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
                'user': user,
                'description': description,
                'like': [],
            }
        })

        self.posts.append({
            'model': 'ibis.Post',
            'pk': pk,
            'fields': {
                'title': title,
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
                'user': user,
                'description': description,
                'like': [],
            }
        })

        self.comments.append({
            'model': 'ibis.Comment',
            'pk': pk,
            'fields': {
                'parent': parent,
                'score': score,
            }
        })

        return pk

    def add_deposit(self, user, amount):
        pk = len(self.deposits) + 1

        sha = hashlib.sha256()
        sha.update(str(pk).encode())
        payment_id = 'ubp:{}'.format(sha.hexdigest())

        self.deposits.append({
            'model': 'ibis.Deposit',
            'pk': pk,
            'fields': {
                'user': user,
                'payment_id': payment_id,
                'amount': amount,
            }
        })

        return pk

    def add_follow(self, source, target):
        user = next((x for x in self.ibisUsers if x['pk'] == source), None)
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
        partial_ibisUsers = copy.deepcopy(self.ibisUsers)
        for x in partial_ibisUsers:
            del x['fields']['following']

        partial_entries = copy.deepcopy(self.entries)
        for x in partial_entries:
            x['fields']['like'] = []

        return [
            self.users,
            partial_ibisUsers,
            self.nonprofit_categories,
            self.nonprofits,
            self.people,
            self.ibisUsers,
            self.deposits,
            partial_entries,
            self.donations,
            self.transactions,
            self.news,
            self.events,
            self.posts,
            self.comments,
            self.entries,
            self.sites,
            self.socialApplications,
        ]


class Command(BaseCommand):
    help = 'Generate/regenerate fixture.json file in ibis/fixtures'

    def add_arguments(self, parser):
        parser.add_argument('--num_person', type=int, required=True)
        parser.add_argument('--num_donation', type=int, required=True)
        parser.add_argument('--num_transaction', type=int, required=True)
        parser.add_argument('--num_news', type=int, required=True)
        parser.add_argument('--num_event', type=int, required=True)
        parser.add_argument('--num_post', type=int, required=True)
        parser.add_argument('--num_comment', type=int, required=True)
        parser.add_argument('--num_follow', type=int, required=True)
        parser.add_argument('--num_rsvp', type=int, required=True)
        parser.add_argument('--num_bookmark', type=int, required=True)
        parser.add_argument('--num_like', type=int, required=True)

    def handle(self, *args, **options):
        self.run(
            num_person=options['num_person'],
            num_donation=options['num_donation'],
            num_transaction=options['num_transaction'],
            num_news=options['num_news'],
            num_event=options['num_event'],
            num_post=options['num_post'],
            num_comment=options['num_comment'],
            num_follow=options['num_follow'],
            num_rsvp=options['num_rsvp'],
            num_bookmark=options['num_bookmark'],
            num_like=options['num_like'],
        )

    def run(
            self,
            num_person,
            num_donation,
            num_transaction,
            num_news,
            num_event,
            num_post,
            num_comment,
            num_follow,
            num_rsvp,
            num_bookmark,
            num_like,
    ):

        random.seed(0)
        model = Model()

        # load data
        markov = Markov(os.path.join(DIR, 'data/corpus'))

        with open(os.path.join(DIR, 'data/nonprofit_categories.json')) as fd:
            np_cat_raw = json.load(fd)

        with open(os.path.join(DIR, 'data/nonprofits.json')) as fd:
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

        # make nonprofit categories from charity navigator categories
        nonprofit_categories = [
            model.add_nonprofit_category(x, np_cat_raw[x]) for x in np_cat_raw
        ]

        # make nonprofits from scraped list of real nonprofits
        nonprofits = [
            model.add_nonprofit(
                x['name'],
                x['description'],
                random.choice(nonprofit_categories),
                random.randint(0, 100),
            ) for x in np_raw
        ]

        # make people
        people_raw = people_raw * (int((num_person - 1) / len(people_raw)) + 1)
        people = [
            model.add_person(x[0], x[1], random.randint(0, 100))
            for x in people_raw[:num_person]
        ]

        # make deposit money for all users
        for person in people:
            model.add_deposit(person, 1000000)

        # initial donations for nonprofits
        for nonprofit in nonprofits:
            donor = random.choice(people)
            model.add_deposit(donor, 1000000)
            model.add_donation(donor, nonprofit, 1000000, 'initial', 0)

        # make random donations
        donations = []
        for i in range(num_donation - len(nonprofits)):
            donor = random.choice(people + nonprofits)
            donations.append(
                model.add_donation(
                    donor,
                    random.choice([x for x in nonprofits if x != donor]),
                    random.randint(1, 10000),
                    markov.generate_markov_text(),
                    random.randint(0, 100),
                ))

        # make random transactions
        transactions = []
        for i in range(num_transaction):
            sender = random.choice(people + nonprofits)
            transactions.append(
                model.add_transaction(
                    sender,
                    random.choice([x for x in people if x != sender]),
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
                    random.choice(nonprofits),
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
                    random.choice(nonprofits),
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

        # make fake comments
        comments = []
        for i in range(num_comment):
            commentable = transactions + donations + news + events + posts\
                + comments
            parent = random.choice(commentable)
            description = markov.generate_markov_text(
                size=random.randint(25, 100))
            comments.append(
                model.add_comment(
                    random.choice(people + nonprofits),
                    parent,
                    description,
                    random.randint(0, 100),
                ))

        # add followers
        for i in range(num_follow):
            source, target = random.sample(people + nonprofits, 2)
            model.add_follow(source, target)

        # add rsvps
        for i in range(num_rsvp):
            model.add_rsvp(
                random.choice(people + nonprofits),
                random.choice(events),
            )

        # add bookmarks
        for i in range(num_bookmark):
            model.add_bookmark(
                random.choice(people + nonprofits),
                random.choice(news + posts))

        # add likes
        likeable = transactions + donations + news + events + posts + comments
        for i in range(num_like):
            model.add_like(
                random.choice(people + nonprofits),
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
