#!/usr/bin/python3

import json
import random

from datetime import datetime, timedelta

import markovgen


class Model:
    def __init__(self):
        self.nonprofit_categories = []
        self.users = []
        self.ibisUsers = []
        self.nonprofits = []
        self.exchanges = []
        self.posts = []
        self.transfers = []
        self.news = []
        self.events = []

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

    def add_nonprofit(self, title, description, category, score):
        pk = len(self.users) + 2

        self.users.append({
            'model': 'users.User',
            'pk': pk,
            'fields': {
                'username':
                '{}_{}'.format(title[:10].lower().replace(' ', '_'), pk),
                'first_name':
                title,
            }
        })

        self.ibisUsers.append({
            'model': 'ibis.IbisUser',
            'pk': pk,
            'fields': {
                'score': score,
            },
        })

        self.nonprofits.append({
            'model': 'ibis.Nonprofit',
            'pk': pk,
            'fields': {
                'title': title,
                'category': [category],
                'description': description,
            }
        })

        return pk

    def add_donation(self, person, nonprofit, amount, description):
        assert nonprofit in [x['pk'] for x in self.nonprofits]
        pk = len(self.posts) + 1

        self.posts.append({
            'model': 'ibis.Post',
            'pk': pk,
            'fields': {
                'user': person,
                'description': description
            }
        })
        self.transfers.append({
            'model': 'ibis.Transfer',
            'pk': pk,
            'fields': {
                'target': nonprofit,
                'amount': amount,
                'like': [],
            }
        })

        return pk

    def add_person(self, first, last, score):
        pk = len(self.users) + 2

        self.users.append({
            'model': 'users.User',
            'pk': pk,
            'fields': {
                'username':
                '{}_{}'.format('{}_{}'.format(first, last)[:10].lower(), pk),
                'first_name':
                first,
                'last_name':
                last,
            }
        })

        self.ibisUsers.append({
            'model': 'ibis.IbisUser',
            'pk': pk,
            'fields': {
                'following': [],
                'score': score,
            }
        })

        return pk

    def add_transaction(self, source, target, amount, description):
        assert source not in [x['pk'] for x in self.nonprofits]
        assert target not in [x['pk'] for x in self.nonprofits]
        pk = len(self.posts) + 1

        self.posts.append({
            'model': 'ibis.Post',
            'pk': pk,
            'fields': {
                'user': source,
                'description': description,
            }
        })
        self.transfers.append({
            'model': 'ibis.Transfer',
            'pk': pk,
            'fields': {
                'target': target,
                'amount': amount,
                'like': [],
            }
        })

        return pk

    def add_news(self, nonprofit, title, description, score):
        assert nonprofit in [x['pk'] for x in self.nonprofits]
        pk = len(self.posts) + 1

        self.posts.append({
            'model': 'ibis.Post',
            'pk': pk,
            'fields': {
                'user': nonprofit,
                'description': description,
            }
        })

        self.news.append({
            'model': 'ibis.News',
            'pk': pk,
            'fields': {
                'title': title,
                'bookmark': [],
                'like': [],
                'score': score,
            }
        })

        return pk

    def add_event(self, nonprofit, title, link, description, date, score):
        assert nonprofit in [x['pk'] for x in self.nonprofits]
        pk = len(self.posts) + 1

        self.posts.append({
            'model': 'ibis.Post',
            'pk': pk,
            'fields': {
                'user': nonprofit,
                'description': description,
            }
        })

        self.events.append({
            'model': 'ibis.Event',
            'pk': pk,
            'fields': {
                'title': title,
                'link': link,
                'rsvp': [],
                'like': [],
                'date': date,
                'score': score,
            }
        })

        return pk

    def add_deposit(self, user, amount):
        pk = len(self.exchanges) + 1

        self.exchanges.append({
            'model': 'ibis.Exchange',
            'pk': pk,
            'fields': {
                'user': user,
                'amount': amount
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

    def add_bookmark(self, person, news):
        news_obj = next((x for x in self.news if x['pk'] == news), None)
        news_obj['fields']['bookmark'].append(person)

    def add_like(self, person, post):
        likeable = self.transfers + self.news + self.events
        post_obj = next((x for x in likeable if x['pk'] == post), None)
        post_obj['fields']['like'].append(person)

    def get_model(self):
        return self.nonprofit_categories + \
            self.users + \
            self.ibisUsers + \
            self.nonprofits + \
            self.exchanges + \
            self.posts + \
            self.transfers + \
            self.news + \
            self.events


def run():

    random.seed(0)
    model = Model()

    # load data
    markov = markovgen.Markov('data/corpus')

    with open('data/nonprofit_categories.json') as fd:
        np_cat_raw = json.load(fd)

    with open('data/nonprofits.json') as fd:
        np_raw = sorted(json.load(fd), key=lambda x: x['title'])

    with open('data/names.txt') as fd:
        people_raw = [x.strip().split(' ') for x in fd.readlines()]

    with open('data/nouns.txt') as fd:
        nouns = [x[0].capitalize() + x[1:].strip() for x in fd.readlines()]

    with open('data/verbs.txt') as fd:
        verbs = [x[0].capitalize() + x[1:].strip() for x in fd.readlines()]

    with open('data/adjectives.txt') as fd:
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

    # make nonprofit categories from charity navigator categories
    nonprofit_categories = [
        model.add_nonprofit_category(x, np_cat_raw[x]) for x in np_cat_raw
    ]

    # make nonprofits from scraped list of real nonprofits
    nonprofits = [
        model.add_nonprofit(
            x['title'],
            x['description'],
            random.choice(nonprofit_categories),
            random.randint(0, 100),
        ) for x in np_raw
    ]

    # make people
    people = [
        model.add_person(x[0], x[1], random.randint(0, 100))
        for x in people_raw[:100]
    ]

    # make deposit money for all users
    for person in people:
        model.add_deposit(person, 10000)

    # make random donations
    donations = []
    for i in range(400):
        donations.append(
            model.add_donation(
                random.choice(people),
                random.choice(nonprofits),
                random.randint(1, 100),
                markov.generate_markov_text(),
            ))

    # make random transactions
    transactions = []
    for i in range(400):
        sample = random.sample(people, 2)
        transactions.append(
            model.add_transaction(
                sample[0],
                sample[1],
                random.randint(1, 100),
                markov.generate_markov_text(),
            ))

    # make fake news
    news = []
    for i in range(200):
        title = 'Breaking: {} {}s {}'.format(
            random.choice(nouns),
            random.choice(verbs),
            random.choice(nouns),
        )
        news.append(
            model.add_news(
                random.choice(nonprofits),
                title,
                markov.generate_markov_text(size=90),
                random.randint(0, 100),
            ))

    # make fake events
    events = []
    date_next = datetime.now()
    for i in range(200):
        title = 'The {} {} {}'.format(
            random.choice(adjectives),
            random.choice(nouns),
            random.choice(event_type),
        )
        date_next += timedelta(hours=random.randint(0, 48))
        events.append(
            model.add_event(
                random.choice(nonprofits),
                title,
                'http://{}.org'.format(title.replace(' ', '_')),
                markov.generate_markov_text(size=60),
                date_next.strftime('%Y-%m-%dT%H:%M:%S+00:00'),
                random.randint(0, 100),
            ))

    # add followers
    for person in people:
        targets = random.sample([p for p in people if p != person],
                                min(random.randint(0, 50),
                                    len(people) - 1))
        targets.extend(
            random.sample(nonprofits,
                          min(random.randint(0, 50), len(nonprofits))))
        for target in targets:
            model.add_follow(person, target)

    # add rsvps
    for person in people:
        event_sample = random.sample(
            events,
            min(random.randint(0, 10), len(events)),
        )
        for event in event_sample:
            model.add_rsvp(person, event)

    # add bookmarks
    for person in people:
        news_sample = random.sample(
            news,
            min(random.randint(0, 10), len(news)),
        )
        for article in news_sample:
            model.add_bookmark(person, article)

    likeable = transactions + donations + news + events

    # add likes
    for person in people:
        likeable_sample = random.sample(
            likeable,
            min(random.randint(0, 100), len(likeable)),
        )
        for post in likeable_sample:
            model.add_like(person, post)

    # save fixtures
    with open('fixtures.json', 'w') as fd:
        json.dump(model.get_model(), fd)


if __name__ == '__main__':
    run()
