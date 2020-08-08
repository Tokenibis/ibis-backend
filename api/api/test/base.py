import os
import json
import logging
import random

from django.core.management import call_command
from django.conf import settings
from django.utils.timezone import now, localtime, utc
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay.node.node import to_global_id
from freezegun import freeze_time

import users.models
import ibis.models as models
import api.schema

logging.disable(logging.CRITICAL)

DIR = os.path.dirname(os.path.realpath(__file__))

NUM_PERSON = 10
NUM_ORGANIZATION = 10
NUM_DEPOSIT = 30
NUM_WITHDRAWAL = 30
NUM_DONATION = 100
NUM_REWARD = 100
NUM_NEWS = 100
NUM_EVENT = 100
NUM_POST = 100
NUM_COMMENT = 100
NUM_FOLLOW = 100
NUM_RSVP = 100
NUM_BOOKMARK = 100
NUM_LIKE = 100

TEST_TIME = localtime(now()).replace(
    year=2020,
    month=4,
    day=5,
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
)

with freeze_time(TEST_TIME.astimezone(utc).date()):
    call_command(
        'make_fixtures',
        num_person=NUM_PERSON,
        num_organization=NUM_ORGANIZATION,
        num_deposit=NUM_DEPOSIT,
        num_withdrawal=NUM_WITHDRAWAL,
        num_donation=NUM_DONATION,
        num_reward=NUM_REWARD,
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
        'CommentList',
        'DepositList',
        'Donation',
        'DonationCreate',
        'DonationForm',
        'DonationList',
        'Event',
        'EventCreate',
        'EventList',
        'EventListFilter',
        'EventUpdate',
        'Finance',
        'FollowCreate',
        'FollowDelete',
        'Home',
        'LikeCreate',
        'LikeDelete',
        'News',
        'NewsCreate',
        'NewsList',
        'NewsUpdate',
        'NotificationClicked',
        'NotificationList',
        'Notifier',
        'NotifierSeen',
        'NotifierUpdate',
        'Organization',
        'OrganizationList',
        'OrganizationUpdate',
        'Person',
        'PersonList',
        'PersonUpdate',
        'Post',
        'PostCreate',
        'PostList',
        'Reward',
        'RewardCreate',
        'RewardForm',
        'RewardList',
        'RsvpCreate',
        'RsvpDelete',
        'Settings',
        'SideMenu',
        'UserList',
        'WithdrawalList',
    ]

    GRAPHQL_SCHEMA = api.schema.schema

    @classmethod
    def setUpTestData(cls):
        cls.gql = {}
        gql_dir = 'graphql/app'
        for filename in os.listdir(os.path.join(DIR, gql_dir)):
            if filename.split('.')[-1] == 'gql':
                with open(os.path.join(DIR, gql_dir, filename)) as fd:
                    cls.gql[filename.split('.')[0]] = fd.read()

    def setUp(self):
        settings.EMAIL_HOST = ''
        assert 'api.middleware.AuthenticateAllMiddleware' not in settings.MIDDLEWARE

        random.seed(0)

        self.assertCountEqual(self.gql.keys(), self.operations)
        assert len(models.Person.objects.all()) == NUM_PERSON
        assert len(models.Organization.objects.all()) == NUM_ORGANIZATION
        assert len(models.Donation.objects.all()) == NUM_DONATION
        assert len(models.Reward.objects.all()) == NUM_REWARD
        assert len(models.News.objects.all()) == NUM_NEWS
        assert len(models.Event.objects.all()) == NUM_EVENT
        assert len(models.Post.objects.all()) == NUM_POST
        assert len(models.Comment.objects.all()) == NUM_COMMENT

        with freeze_time(TEST_TIME.astimezone(utc).date()):
            self.staff = users.models.GeneralUser.objects.create(
                username='staff',
                first_name='Staffy',
                last_name='McStaffface',
                email='staff@example.come',
                is_superuser=True,
            )

            self.me_person = models.Person.objects.create(
                username='person',
                password='password',
                first_name='Person',
                last_name='McPersonFace',
                email='person@example.com',
            )

            self.me_organization = models.Organization.objects.create(
                username='organization',
                password='password',
                first_name='Organization',
                last_name='McOrganizationFace',
                email='organization@example.com',
                category=models.OrganizationCategory.objects.first(),
            )

            models.Deposit.objects.create(
                user=self.me_person,
                amount=300,
                payment_id='unique_1',
                category=models.DepositCategory.objects.first(),
            )

            models.Deposit.objects.create(
                user=self.me_organization,
                amount=400,
                payment_id='unique_2',
                category=models.DepositCategory.objects.first(),
            )

            self.organization = models.Organization.objects.all().first()
            self.person = models.Person.objects.all().first()
            self.donation = models.Donation.objects.all().first()
            self.reward = models.Reward.objects.all().first()
            self.news = models.News.objects.all().first()
            self.event = models.Event.objects.all().first()
            self.post = models.Post.objects.all().first()

            self.me_person.gid = to_global_id('UserNode', self.me_person.id)
            self.me_organization.gid = to_global_id('UserNode',
                                                 self.me_organization.id)
            self.organization.gid = to_global_id('UserNode',
                                              self.organization.id)
            self.person.gid = to_global_id('UserNode', self.person.id)
            self.donation.gid = to_global_id('EntryNode', self.donation.id)
            self.reward.gid = to_global_id('EntryNode',
                                                self.reward.id)
            self.news.gid = to_global_id('EntryNode', self.news.id)
            self.event.gid = to_global_id('EntryNode', self.event.id)
            self.post.gid = to_global_id('EntryNode', self.post.id)

            # make sure that me_person, me_organization, and person have notifications
            donation_me_person = models.Donation.objects.create(
                user=self.me_person,
                target=self.organization,
                amount=100,
                description='My donation',
            )
            donation_me_organization = models.Donation.objects.create(
                user=self.me_organization,
                target=self.organization,
                amount=100,
                description='My donation',
            )
            donation_person = models.Donation.objects.create(
                user=self.person,
                target=self.organization,
                amount=100,
                description='Person\'s donation',
            )

            # make sure me_organization has one withdrawal
            models.Withdrawal.objects.create(
                user=self.me_organization,
                amount=100,
                description='This is a withdrawal',
            )

            self._client.force_login(self.person)
            self.query(
                self.gql['LikeCreate'],
                op_name='LikeCreate',
                variables={
                    'user': self.person.gid,
                    'target': to_global_id('DonationNode',
                                           donation_me_person.id),
                },
            )
            self.query(
                self.gql['LikeCreate'],
                op_name='LikeCreate',
                variables={
                    'user':
                    self.person.gid,
                    'target':
                    to_global_id('DonationNode', donation_me_organization.id),
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

            self.notification = self.me_person.notifier.notification_set.first(
            )

            # make sure that self.person has things to hide for later

            models.Deposit.objects.create(
                user=self.me_person,
                amount=200,
                payment_id='unique_3',
                category=models.DepositCategory.objects.first(),
            )

            models.Donation.objects.create(
                user=self.person,
                target=self.organization,
                amount=100,
                description='External donation',
            )

            models.Reward.objects.create(
                user=self.person,
                target=models.Person.objects.exclude(
                    pk=self.person.id).first(),
                amount=100,
                description='External reward',
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
