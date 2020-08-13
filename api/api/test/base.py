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

# logging.disable(logging.CRITICAL)

DIR = os.path.dirname(os.path.realpath(__file__))

NUM_BOOKMARK = 100
NUM_BOT = 3
NUM_ACTIVITY = 100
NUM_COMMENT = 100
NUM_DEPOSIT = 30
NUM_DONATION = 100
NUM_EVENT = 100
NUM_FOLLOW = 100
NUM_LIKE = 100
NUM_MENTION = 100
NUM_NEWS = 100
NUM_ORGANIZATION = 10
NUM_PERSON = 10
NUM_POST = 100
NUM_REWARD = 100
NUM_RSVP = 100
NUM_WITHDRAWAL = 30

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
        num_bookmark=NUM_BOOKMARK,
        num_bot=NUM_BOT,
        num_activity=NUM_ACTIVITY,
        num_comment=NUM_COMMENT,
        num_deposit=NUM_DEPOSIT,
        num_donation=NUM_DONATION,
        num_event=NUM_EVENT,
        num_follow=NUM_FOLLOW,
        num_like=NUM_LIKE,
        num_like=NUM_MENTION,
        num_news=NUM_NEWS,
        num_organization=NUM_ORGANIZATION,
        num_person=NUM_PERSON,
        num_post=NUM_POST,
        num_reward=NUM_REWARD,
        num_rsvp=NUM_RSVP,
        num_withdrawal=NUM_WITHDRAWAL,
    )


class BaseTestCase(GraphQLTestCase):
    fixtures = sorted([
        x.split('/')[-1] for x in os.listdir(os.path.join(DIR, '../fixtures'))
    ])
    operations = [
        'Activity',
        'ActivityCreate',
        'ActivityList',
        'ActivityUpdate',
        'BookmarkCreate',
        'BookmarkDelete',
        'Bot',
        'BotList',
        'BotUpdate',
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
        if 'api.middleware.AuthenticateAllMiddleware' in settings.MIDDLEWARE:
            settings.MIDDLEWARE.remove('api.middleware.AuthenticateAllMiddleware')

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

            self.me_bot = models.Bot.objects.create(
                username='bot',
                password='password',
                first_name='Bot',
                last_name='McBotFace',
                email='bot@example.com',
            )

            models.Deposit.objects.create(
                user=self.me_person,
                amount=301,
                description='unique_1',
                category=models.ExchangeCategory.objects.first(),
            )

            models.Withdrawal.objects.create(
                user=self.me_person,
                amount=1,
                description='unique_1',
                category=models.ExchangeCategory.objects.first(),
            )

            models.Deposit.objects.create(
                user=self.me_organization,
                amount=401,
                description='unique_2',
                category=models.ExchangeCategory.objects.first(),
            )

            models.Deposit.objects.create(
                user=self.me_bot,
                amount=300,
                description='unique_bot_1',
                category=models.ExchangeCategory.objects.first(),
            )

            models.Withdrawal.objects.create(
                user=self.me_organization,
                amount=1,
                description='unique_2',
                category=models.ExchangeCategory.objects.first(),
            )

            models.Withdrawal.objects.create(
                user=self.me_bot,
                amount=1,
                description='unique_2',
                category=models.ExchangeCategory.objects.first(),
            )

            self.organization = models.Organization.objects.all().first()
            self.person = models.Person.objects.all().first()
            self.donation = models.Donation.objects.all().first()
            self.news = models.News.objects.create(
                user=self.me_organization,
                title='news',
                image='link',
                description='description',
            )
            self.event = models.Event.objects.create(
                user=self.me_organization,
                title='event',
                image='link',
                description='description',
                date=localtime(),
                duration=60,
            )
            self.post = models.Post.objects.create(
                user=self.me_person,
                title='post',
                description='description',
            )
            self.activity = models.Activity.objects.create(
                user=self.me_bot,
                title='activity',
                description='description',
                active=True,
            )

            self.me_person.gid = to_global_id('UserNode', self.me_person.id)
            self.me_organization.gid = to_global_id('UserNode',
                                                    self.me_organization.id)
            self.me_bot.gid = to_global_id('UserNode', self.me_bot.id)
            self.organization.gid = to_global_id('UserNode',
                                                 self.organization.id)
            self.person.gid = to_global_id('UserNode', self.person.id)
            self.donation.gid = to_global_id('EntryNode', self.donation.id)
            self.news.gid = to_global_id('EntryNode', self.news.id)
            self.event.gid = to_global_id('EntryNode', self.event.id)
            self.post.gid = to_global_id('EntryNode', self.post.id)
            self.activity.gid = to_global_id('EntryNode', self.activity.id)

            # make sure that me_person, me_organization, and person have notifications
            donation_me_person = models.Donation.objects.create(
                user=self.me_person,
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
                category=models.ExchangeCategory.objects.get(title='admin'),
            )

            self._client.force_login(self.person)
            self.query(
                self.gql['LikeCreate'],
                op_name='LikeCreate',
                variables={
                    'user': self.person.gid,
                    'target': to_global_id('EntryNode',
                                           donation_me_person.id),
                },
            )
            self._client.force_login(self.me_person)
            self.query(
                self.gql['LikeCreate'],
                op_name='LikeCreate',
                variables={
                    'user': self.me_person.gid,
                    'target': to_global_id('EntryNode', donation_person.id),
                },
            )
            self._client.logout()

            self.notification = self.me_person.notifier.notification_set.first(
            )

            # make sure that self.person has things to hide for later

            models.Deposit.objects.create(
                user=self.me_person,
                amount=200,
                description='unique_3',
                category=models.ExchangeCategory.objects.first(),
            )

            models.Donation.objects.create(
                user=self.person,
                target=self.organization,
                amount=100,
                description='External donation',
            )

            models.Reward.objects.create(
                user=models.Bot.objects.first(),
                target=self.person,
                amount=100,
                description='External donation',
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
