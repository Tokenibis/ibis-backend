import os
import json
import logging
import random
from django.core.management import call_command
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay.node.node import to_global_id

import users.models
import ibis.models as models
import api.schema

logging.disable(logging.CRITICAL)

DIR = os.path.dirname(os.path.realpath(__file__))

NUM_PERSON = 10
NUM_DONATION = 100
NUM_TRANSACTION = 100
NUM_NEWS = 100
NUM_EVENT = 100
NUM_POST = 100
NUM_COMMENT = 100

NUM_FOLLOW = 100
NUM_RSVP = 100
NUM_BOOKMARK = 100
NUM_LIKE = 100

call_command(
    'make_fixtures',
    num_person=NUM_PERSON,
    num_donation=NUM_DONATION,
    num_transaction=NUM_TRANSACTION,
    num_news=NUM_NEWS,
    num_event=NUM_EVENT,
    num_post=NUM_POST,
    num_comment=NUM_COMMENT,
    num_follow=NUM_FOLLOW,
    num_rsvp=NUM_RSVP,
    num_bookmark=NUM_BOOKMARK,
    num_like=NUM_LIKE,
)


class BaseTestCase(GraphQLTestCase):
    fixtures = sorted([
        x.split('/')[-1] for x in os.listdir(os.path.join(DIR, '../fixtures'))
    ])
    operations = [
        'BookmarkCreate',
        'BookmarkDelete',
        'CommentCreate',
        'CommentTree',
        'Deposit',
        'DepositList',
        'Donation',
        'DonationCreate',
        'DonationForm',
        'DonationList',
        'Event',
        'EventList',
        'EventListFilter',
        'FollowCreate',
        'FollowDelete',
        'Home',
        'IbisUserList',
        'LikeCreate',
        'LikeDelete',
        'News',
        'NewsList',
        'Nonprofit',
        'NonprofitList',
        'NotificationClicked',
        'NotificationList',
        'Notifier',
        'NotifierSeen',
        'NotifierSettingsUpdate',
        'Person',
        'PersonList',
        'PersonSettingsUpdate',
        'Post',
        'PostCreate',
        'PostList',
        'RsvpCreate',
        'RsvpDelete',
        'Settings',
        'SideMenu',
        'Transaction',
        'TransactionCreate',
        'TransactionForm',
        'TransactionList',
    ]

    GRAPHQL_SCHEMA = api.schema.schema

    @classmethod
    def setUpTestData(cls):
        cls.gql = {}
        gql_dir = 'graphql/operations'
        for filename in os.listdir(os.path.join(DIR, gql_dir)):
            if filename.split('.')[-1] == 'gql':
                with open(os.path.join(DIR, gql_dir, filename)) as fd:
                    cls.gql[filename.split('.')[0]] = fd.read()

    def setUp(self):
        random.seed(0)

        self.assertCountEqual(self.gql.keys(), self.operations)
        assert len(models.Person.objects.all()) == NUM_PERSON
        assert len(models.Donation.objects.all()) == NUM_DONATION
        assert len(models.Transaction.objects.all()) == NUM_TRANSACTION
        assert len(models.News.objects.all()) == NUM_NEWS
        assert len(models.Event.objects.all()) == NUM_EVENT
        assert len(models.Post.objects.all()) == NUM_POST
        assert len(models.Comment.objects.all()) == NUM_COMMENT

        self.staff = users.models.User.objects.create(
            username='staff',
            first_name='Staffy',
            last_name='McStaffface',
            email='staff@example.come',
            is_staff=True,
        )

        self.me_person = models.Person.objects.create(
            username='person',
            password='password',
            first_name='Person',
            last_name='McPersonFace',
            email='person@example.com',
        )

        self.me_nonprofit = models.Nonprofit.objects.create(
            username='nonprofit',
            password='password',
            first_name='Nonprofit',
            last_name='McNonprofitFace',
            email='nonprofit@example.com',
            category=models.NonprofitCategory.objects.first(),
        )

        models.Deposit.objects.create(
            user=self.me_person,
            amount=300,
            payment_id='unique_1',
            category=models.DepositCategory.objects.first(),
        )

        models.Deposit.objects.create(
            user=self.me_nonprofit,
            amount=300,
            payment_id='unique_2',
            category=models.DepositCategory.objects.first(),
        )

        self.nonprofit = models.Nonprofit.objects.all().first()
        self.person = models.Person.objects.all().first()
        self.donation = models.Donation.objects.all().first()
        self.transaction = models.Transaction.objects.all().first()
        self.news = models.News.objects.all().first()
        self.event = models.Event.objects.all().first()
        self.post = models.Post.objects.all().first()

        self.me_person.gid = to_global_id('PersonNode', self.me_person.id)
        self.me_nonprofit.gid = to_global_id('NonprofitNode',
                                             self.me_nonprofit.id)
        self.nonprofit.gid = to_global_id('NonprofitNode', self.nonprofit.id)
        self.person.gid = to_global_id('PersonNode', self.person.id)
        self.donation.gid = to_global_id('DonationNode', self.donation.id)
        self.transaction.gid = to_global_id('TransactionNode',
                                            self.transaction.id)
        self.news.gid = to_global_id('NewsNode', self.news.id)
        self.event.gid = to_global_id('EventNode', self.event.id)
        self.post.gid = to_global_id('PostNode', self.post.id)

        # make sure that me_person, me_nonprofit, and person have notifications
        donation_me_person = models.Donation.objects.create(
            user=self.me_person,
            target=self.nonprofit,
            amount=100,
            description='My donation',
        )
        donation_me_nonprofit = models.Donation.objects.create(
            user=self.me_nonprofit,
            target=self.nonprofit,
            amount=100,
            description='My donation',
        )
        donation_person = models.Donation.objects.create(
            user=self.person,
            target=self.nonprofit,
            amount=100,
            description='Person\'s donation',
        )

        self._client.force_login(self.person)
        self.query(
            self.gql['LikeCreate'],
            op_name='LikeCreate',
            variables={
                'user': self.person.gid,
                'target': to_global_id('DonationNode', donation_me_person.id),
            },
        )
        self.query(
            self.gql['LikeCreate'],
            op_name='LikeCreate',
            variables={
                'user': self.person.gid,
                'target': to_global_id('DonationNode',
                                       donation_me_nonprofit.id),
            },
        )
        self._client.logout()
        self._client.force_login(self.me_person)
        self.query(
            self.gql['LikeCreate'],
            op_name='LikeCreate',
            variables={
                'user': self.me_person.gid,
                'target': to_global_id('DonationNode', donation_person.id),
            },
        )
        self._client.logout()

        self.notification = self.me_person.notifier.notification_set.first()

        # make sure that self.person has things to hide for later

        models.Deposit.objects.create(
            user=self.me_person,
            amount=200,
            payment_id='unique_3',
            category=models.DepositCategory.objects.first(),
        )

        models.Donation.objects.create(
            user=self.person,
            target=self.nonprofit,
            amount=100,
            description='External donation',
        )

        models.Transaction.objects.create(
            user=self.person,
            target=models.Person.objects.exclude(pk=self.person.id).first(),
            amount=100,
            description='External transaction',
        )

    def query(self, query, op_name, variables):
        body = {"query": query}
        if op_name:
            body["operationName"] = op_name
        if variables:
            body["variables"] = variables
        resp = self._client.post(
            self.GRAPHQL_URL,
            json.dumps(body),
            content_type="application/json")
        return resp
