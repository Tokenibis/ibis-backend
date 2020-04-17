import os
import re
import json
import logging
import random
from django.utils.timezone import now, timedelta
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.conf import settings
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay.node.node import to_global_id

import users.models
import tracker.models
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


class APITestCase(GraphQLTestCase):
    fixtures = sorted([
        x.split('/')[-1] for x in os.listdir(os.path.join(DIR, 'fixtures'))
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
        gql_dir = 'test/graphql/operations'
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
            category_id=models.NonprofitCategory.objects.first().id,
        )

        models.Deposit.objects.create(
            user=self.me_person,
            amount=300,
            payment_id='unique_1',
        )

        models.Deposit.objects.create(
            user=self.me_nonprofit,
            amount=300,
            payment_id='unique_2',
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

    def run_all(self, user):
        success = {}
        init_tracker_len = len(tracker.models.Log.objects.all())

        result = json.loads(
            self.query(
                self.gql['DonationCreate'],
                op_name='DonationCreate',
                variables={
                    'user': to_global_id('IbisUserNode', user.id),
                    'target': self.nonprofit.gid,
                    'amount': 100,
                    'description': 'This is a donation',
                },
            ).content)
        success['DonationCreate'] = 'errors' not in result and result['data'][
            'createDonation']['donation']['id']

        result = json.loads(
            self.query(
                self.gql['TransactionCreate'],
                op_name='TransactionCreate',
                variables={
                    'user': to_global_id('IbisUserNode', user.id),
                    'target': self.person.gid,
                    'amount': 100,
                    'description': 'This is a transaction',
                },
            ).content)
        success['TransactionCreate'] = 'errors' not in result and result[
            'data']['createTransaction']['transaction']['id']

        result = json.loads(
            self.query(
                self.gql['PostCreate'],
                op_name='PostCreate',
                variables={
                    'user': user.gid,
                    'title': 'This is a title',
                    'description': 'This is a description',
                },
            ).content)
        success['PostCreate'] = 'errors' not in result and result['data'][
            'createPost']['post']['id']

        result = json.loads(
            self.query(
                self.gql['CommentCreate'],
                op_name='CommentCreate',
                variables={
                    'user': user.gid,
                    'parent': self.donation.gid,
                    'description': 'This is a description',
                    'self': user.gid,
                },
            ).content)
        success['CommentCreate'] = 'errors' not in result and result['data'][
            'createComment']['comment']['id']

        result = json.loads(
            self.query(
                self.gql['FollowCreate'],
                op_name='FollowCreate',
                variables={
                    'user': user.gid,
                    'target': self.person.gid,
                },
            ).content)
        success['FollowCreate'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['LikeCreate'],
                op_name='LikeCreate',
                variables={
                    'user': user.gid,
                    'target': self.donation.gid,
                },
            ).content)
        success['LikeCreate'] = 'errors' not in result and result['data'][
            'createLike']['state']

        result = json.loads(
            self.query(
                self.gql['BookmarkCreate'],
                op_name='BookmarkCreate',
                variables={
                    'user': user.gid,
                    'target': self.news.gid,
                },
            ).content)
        success['BookmarkCreate'] = 'errors' not in result and result['data'][
            'createBookmark']['state']

        result = json.loads(
            self.query(
                self.gql['RsvpCreate'],
                op_name='RsvpCreate',
                variables={
                    'user': user.gid,
                    'target': self.event.gid,
                },
            ).content)

        success['RsvpCreate'] = 'errors' not in result and result['data'][
            'createRsvp']['state']

        result = json.loads(
            self.query(
                self.gql['Nonprofit'],
                op_name='Nonprofit',
                variables={
                    'id': self.nonprofit.gid,
                },
            ).content)
        success['Nonprofit'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['Person'],
                op_name='Person',
                variables={
                    'id': user.gid,
                },
            ).content)
        success['Person'] = 'errors' not in result and bool(
            result['data']['person']['id'])

        result = json.loads(
            self.query(
                self.gql['Donation'],
                op_name='Donation',
                variables={
                    'id': self.donation.gid,
                },
            ).content)
        success['Donation'] = 'errors' not in result and bool(
            result['data']['donation']['id'])

        result = json.loads(
            self.query(
                self.gql['Transaction'],
                op_name='Transaction',
                variables={
                    'id': self.transaction.gid,
                },
            ).content)
        success['Transaction'] = 'errors' not in result and bool(
            result['data']['transaction']['id'])

        result = json.loads(
            self.query(
                self.gql['News'],
                op_name='News',
                variables={
                    'id': self.news.gid,
                },
            ).content)
        success['News'] = 'errors' not in result and bool(
            result['data']['news']['id'])

        result = json.loads(
            self.query(
                self.gql['Event'],
                op_name='Event',
                variables={
                    'id': self.event.gid,
                },
            ).content)
        success['Event'] = 'errors' not in result and bool(
            result['data']['event']['id'])

        result = json.loads(
            self.query(
                self.gql['Post'],
                op_name='Post',
                variables={
                    'id': self.post.gid,
                },
            ).content)
        success['Post'] = 'errors' not in result and bool(
            result['data']['post']['id'])

        result = json.loads(
            self.query(
                self.gql['Home'],
                op_name='Home',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                },
            ).content)
        success['Home'] = 'errors' not in result and bool(
            result['data']['ibisUser']['id'])

        result = json.loads(
            self.query(
                self.gql['SideMenu'],
                op_name='SideMenu',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                },
            ).content)
        success['SideMenu'] = 'errors' not in result and bool(
            result['data']['ibisUser']['id'])

        result = json.loads(
            self.query(
                self.gql['Settings'],
                op_name='Settings',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                },
            ).content)
        success['Settings'] = 'errors' not in result and bool(
            result['data']['ibisUser']['notifier']['id'])

        result = json.loads(
            self.query(
                self.gql['Notifier'],
                op_name='Notifier',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                },
            ).content)
        success['Notifier'] = 'errors' not in result and (
            result['data']['ibisUser']['notifier']['id'] == to_global_id(
                'NotifierNode', user.id))

        result = json.loads(
            self.query(
                self.gql['NonprofitList'],
                op_name='NonprofitList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['NonprofitList'] = 'errors' not in result and len(
            result['data']['allNonprofits']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['PersonList'],
                op_name='PersonList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['PersonList'] = 'errors' not in result and len(
            result['data']['allPeople']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['DonationList'],
                op_name='DonationList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['DonationList'] = 'errors' not in result and len(
            result['data']['allDonations']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['TransactionList'],
                op_name='TransactionList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['TransactionList'] = 'errors' not in result and len(
            result['data']['allTransactions']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['PostList'],
                op_name='PostList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['PostList'] = 'errors' not in result and len(
            result['data']['allPosts']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['NewsList'],
                op_name='NewsList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['NewsList'] = 'errors' not in result and len(
            result['data']['allNews']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['EventList'],
                op_name='EventList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['EventList'] = 'errors' not in result and len(
            result['data']['allEvents']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['EventListFilter'],
                op_name='EventListFilter',
                variables={
                    'beginDate': str(now()),
                    'endDate': str(now() + timedelta(hours=24 * 365)),
                },
            ).content)
        success['EventListFilter'] = 'errors' not in result and len(
            result['data']['allEvents']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['CommentTree'],
                op_name='CommentTree',
                variables={
                    'hasParent': self.donation.gid,
                    'self': user.gid,
                },
            ).content)
        success['CommentTree'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['Deposit'],
                op_name='Deposit',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                },
            ).content)
        success['Deposit'] = 'errors' not in result and bool(
            result['data']['ibisUser']['id'])

        result = json.loads(
            self.query(
                self.gql['DepositList'],
                op_name='DepositList',
                variables={
                    'byUser': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['DepositList'] = 'errors' not in result and bool(
            len(result['data']['allDeposits']['edges']) > 0)

        result = json.loads(
            self.query(
                self.gql['NotificationList'],
                op_name='NotificationList',
                variables={
                    'forUser': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['NotificationList'] = 'errors' not in result and bool(
            len(result['data']['allNotifications']['edges']) > 0)

        result = json.loads(
            self.query(
                self.gql['LikeDelete'],
                op_name='LikeDelete',
                variables={
                    'user': user.gid,
                    'target': self.donation.gid,
                },
            ).content)
        success['LikeDelete'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['FollowDelete'],
                op_name='FollowDelete',
                variables={
                    'user': user.gid,
                    'target': self.person.gid,
                },
            ).content)
        success['FollowDelete'] = 'errors' not in result and not result[
            'data']['deleteFollow']['state']

        result = json.loads(
            self.query(
                self.gql['BookmarkDelete'],
                op_name='BookmarkDelete',
                variables={
                    'user': user.gid,
                    'target': self.news.gid,
                },
            ).content)
        success['BookmarkDelete'] = 'errors' not in result and not result[
            'data']['deleteBookmark']['state']

        result = json.loads(
            self.query(
                self.gql['RsvpDelete'],
                op_name='RsvpDelete',
                variables={
                    'user': user.gid,
                    'target': self.event.gid,
                },
            ).content)
        success['RsvpDelete'] = 'errors' not in result and not result['data'][
            'deleteRsvp']['state']

        result = json.loads(
            self.query(
                self.gql['DonationForm'],
                op_name='DonationForm',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                    'target': self.nonprofit.gid,
                },
            ).content)
        success['DonationForm'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['TransactionForm'],
                op_name='TransactionForm',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                    'target': self.person.gid,
                },
            ).content)
        success['TransactionForm'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['PersonSettingsUpdate'],
                op_name='PersonSettingsUpdate',
                variables={
                    'id': user.gid,
                    'visibilityDonation': models.Person.PUBLIC,
                    'visibilityTransaction': models.Person.PUBLIC,
                },
            ).content)
        success['PersonSettingsUpdate'] = 'errors' not in result and result[
            'data']['updatePerson']['person']['id']

        result = json.loads(
            self.query(
                self.gql['NotifierSettingsUpdate'],
                op_name='NotifierSettingsUpdate',
                variables={
                    'id': user.gid,
                    'emailFollow': True,
                    'emailDonation': True,
                    'emailTransaction': True,
                },
            ).content)
        success['NotifierSettingsUpdate'] = 'errors' not in result and result[
            'data']['updateNotifier']['notifier']['id']

        result = json.loads(
            self.query(
                self.gql['NotifierSeen'],
                op_name='NotifierSeen',
                variables={
                    'id': to_global_id('NotifierNode', user.id),
                    'lastSeen': str(now()),
                },
            ).content)
        success['NotifierSeen'] = 'errors' not in result and result['data'][
            'updateNotifier']['notifier']['id']

        notification = user.notifier.notification_set.first()

        result = json.loads(
            self.query(
                self.gql['NotificationClicked'],
                op_name='NotificationClicked',
                variables={
                    'id': to_global_id('NotificationNode', notification.id),
                    'lastSeen': str(now()),
                },
            ).content)
        success['NotificationClicked'] = 'errors' not in result and result[
            'data']['updateNotification']['notification']['id']

        assert len(tracker.models.Log.objects.all()) - init_tracker_len == len(
            success)

        return success

    def run_privacy(self, person):
        success = {}

        result = json.loads(
            self.query(
                self.gql['DonationList'],
                op_name='DonationList',
                variables={
                    'byUser': person.gid,
                    'orderBy': '-created',
                    'first': 2,
                },
            ).content)
        success['DonationList'] = 'errors' not in result and any(
            x['node']['user']['id'] == to_global_id('IbisUserNode', person.id)
            for x in result['data']['allDonations']['edges'])

        result = json.loads(
            self.query(
                self.gql['TransactionList'],
                op_name='TransactionList',
                variables={
                    'byUser': person.gid,
                    'orderBy': '-created',
                },
            ).content)
        success['TransactionList'] = 'errors' not in result and any(
            x['node']['user']['id'] == to_global_id('IbisUserNode', person.id)
            for x in result['data']['allTransactions']['edges'])

        return success

    # staff can do everything
    def test_staff(self):
        self._client.force_login(self.staff)
        assert all(self.run_all(self.me_person).values())

    # anonymous users can't do anything
    def test_anonymous(self):
        assert not any(self.run_all(self.me_person).values())

    # logged in users can see all of their own information
    def test_person(self):
        self._client.force_login(self.me_person)
        assert all(self.run_all(self.me_person).values())

    # logged in users can see all of their own information
    def test_nonprofit(self):
        self._client.force_login(self.me_nonprofit)
        assert all(x[0] for x in self.run_all(self.me_nonprofit).items()
                   if x[1] not in ['Person', 'PersonSettingsUpdate'])

    # logged in users can see some of other people's information
    def test_other_public(self):
        expected = {
            'BookmarkCreate': False,
            'BookmarkDelete': False,
            'CommentCreate': False,
            'CommentTree': True,
            'DepositList': False,
            'Donation': True,
            'DonationCreate': False,
            'DonationForm': True,
            'DonationList': True,
            'Event': True,
            'EventList': True,
            'EventListFilter': True,
            'FollowCreate': False,
            'FollowDelete': False,
            'Home': True,
            'LikeCreate': False,
            'LikeDelete': False,
            'News': True,
            'NewsList': True,
            'Nonprofit': True,
            'NonprofitList': True,
            'NotificationClicked': False,
            'NotificationList': False,
            'Notifier': False,
            'NotifierSeen': False,
            'NotifierSettingsUpdate': False,
            'Person': True,
            'PersonList': True,
            'PersonSettingsUpdate': False,
            'Post': True,
            'PostCreate': False,
            'PostList': True,
            'RsvpCreate': False,
            'RsvpDelete': False,
            'Settings': False,
            'SideMenu': True,
            'Transaction': True,
            'TransactionCreate': False,
            'TransactionForm': True,
            'TransactionList': True,
        }

        self.person.visibility_donation = models.Person.PUBLIC
        self.person.visibility_transaction = models.Person.PUBLIC
        self.person.save()

        self._client.force_login(self.me_person)
        result = self.run_all(self.person)
        assert (result[x] == expected[x] for x in result)

    # anyone can see public visibility
    def test_privacy_public(self):
        self.person.visibility_donation = models.Person.PUBLIC
        self.person.visibility_transaction = models.Person.PUBLIC
        self.person.save()

        self._client.force_login(self.me_person)
        assert all(self.run_privacy(self.person).values())

    # nobody can see private visibility except self
    def test_privacy_private(self):
        self.person.visibility_donation = models.Person.PRIVATE
        self.person.visibility_transaction = models.Person.PRIVATE
        self.person.save()

        self._client.force_login(self.me_person)
        assert not any(self.run_privacy(self.person).values())

        self._client.force_login(self.person)
        assert all(self.run_privacy(self.person).values())

    # only people being followed have visibility if set to 'following'
    def test_privacy_following(self):
        self.person.visibility_donation = models.Person.FOLLOWING
        self.person.visibility_transaction = models.Person.FOLLOWING
        self.person.save()

        self._client.force_login(self.me_person)
        assert not any(self.run_privacy(self.person).values())

        self.person.following.add(self.me_person)
        self.person.save()

        self._client.force_login(self.me_person)
        assert all(self.run_privacy(self.person).values())

    # make sure that money constraints work
    def test_money_limits(self):
        self._client.force_login(self.me_person)

        def transfer(op_name, target, amount):
            return 'errors' not in json.loads(
                self.query(
                    self.gql[op_name],
                    op_name=op_name,
                    variables={
                        'user': self.me_person.gid,
                        'target': target.gid,
                        'amount': amount,
                        'description': 'This is a description',
                    },
                ).content)

        models.Deposit.objects.create(
            user=self.me_person,
            amount=int(
                (settings.MAX_TRANSFER - self.me_person.balance()) * 1.5),
            payment_id='unique_test_money_limit_donation',
        )

        assert not transfer('DonationCreate', self.nonprofit, -1)
        assert not transfer('DonationCreate', self.nonprofit, 0.5)
        assert not transfer('DonationCreate', self.nonprofit, 0)
        assert not transfer('DonationCreate', self.nonprofit,
                            settings.MAX_TRANSFER + 1)
        assert transfer('DonationCreate', self.nonprofit,
                        settings.MAX_TRANSFER)
        assert transfer('DonationCreate', self.nonprofit,
                        self.me_person.balance())
        assert not transfer('DonationCreate', self.nonprofit, 1)

        models.Deposit.objects.create(
            user=self.me_person,
            amount=int(
                (settings.MAX_TRANSFER - self.me_person.balance()) * 1.5),
            payment_id='unique_test_money_limit_transaction',
        )

        assert not transfer('TransactionCreate', self.person, -1)
        assert not transfer('TransactionCreate', self.person, 0.5)
        assert not transfer('TransactionCreate', self.person, 0)
        assert not transfer('TransactionCreate', self.person,
                            settings.MAX_TRANSFER + 1)
        assert transfer('TransactionCreate', self.person,
                        settings.MAX_TRANSFER)
        assert transfer('TransactionCreate', self.person,
                        self.me_person.balance())
        assert not transfer('TransactionCreate', self.person, 1)

    # send money around randomly and make sure that balances agree at the end
    def test_money_dynamic(self):
        def deposit(user, amount):
            self._client.force_login(self.staff)
            result = json.loads(
                self.query(
                    '''
                    mutation DepositCreate($user: ID! $amount: Int! $paymentId: String!) {
                        createDeposit(user: $user amount: $amount paymentId: $paymentId) {
                            deposit {
                                id
                            }
                        }
                    }
                    ''',
                    op_name='DepositCreate',
                    variables={
                        'user':
                        to_global_id('PersonNode', user.id),
                        'amount':
                        amount,
                        'paymentId':
                        'unique_{}_{}'.format(
                            user.username,
                            len(user.deposit_set.all()),
                        ),
                    },
                ).content)
            self._client.logout()
            return result

        def donate(user, target, amount):
            self._client.force_login(user)
            result = json.loads(
                self.query(
                    self.gql['DonationCreate'],
                    op_name='DonationCreate',
                    variables={
                        'user': to_global_id('IbisUserNode', user.id),
                        'target': to_global_id('NonprofitNode', target.id),
                        'amount': amount,
                        'description': 'This is a donation',
                    },
                ).content)
            self._client.logout()
            return result

        def transact(user, target, amount):
            self._client.force_login(user)
            result = json.loads(
                self.query(
                    self.gql['TransactionCreate'],
                    op_name='TransactionCreate',
                    variables={
                        'user': to_global_id('IbisUserNode', user.id),
                        'target': to_global_id('PersonNode', target.id),
                        'amount': amount,
                        'description': 'This is a transaction',
                    },
                ).content)
            self._client.logout()
            return result

        def withdraw(user, amount):
            self._client.force_login(self.staff)
            result = json.loads(
                self.query(
                    '''
                    mutation WithdrawalCreate($user: ID! $amount: Int!) {
                        createWithdrawal(user: $user amount: $amount) {
                            withdrawal {
                                id
                            }
                        }
                    }
                    ''',
                    op_name='WithdrawalCreate',
                    variables={
                        'user': to_global_id('NonprofitNode', user.id),
                        'amount': amount,
                    },
                ).content)
            self._client.logout()
            return result

        person_state = {
            x: {
                'balance': x.balance(),
                'donated': x.donated(),
            }
            for x in models.Person.objects.all()
        }

        nonprofit_state = {
            x: {
                'balance': x.balance(),
                'donated': x.donated(),
                'fundraised': x.fundraised(),
            }
            for x in models.Nonprofit.objects.all()
        }

        step = sum(person_state[x]['balance']
                   for x in person_state) / len(person_state) / 10

        for _ in range(200):
            choice = random.choice([deposit, donate, transact, withdraw])
            amount = random.randint(1, min(step * 2 - 1,
                                           settings.MAX_TRANSFER))

            if choice == deposit:
                user = random.choice(list(person_state.keys()))
                assert 'errors' not in deposit(user, amount)

                person_state[user]['balance'] += amount

            elif choice == donate:
                if random.random() < 0.8:  # person donates
                    user = random.choice(list(person_state.keys()))
                    target = random.choice(list(nonprofit_state.keys()))
                    result = donate(user, target, amount)

                    if person_state[user]['balance'] - amount >= 0:
                        assert 'errors' not in result
                        person_state[user]['balance'] -= amount
                        person_state[user]['donated'] += amount
                        nonprofit_state[target]['balance'] += amount
                        nonprofit_state[target]['fundraised'] += amount
                    else:
                        assert 'errors' in result
                else:  # nonprofit donates
                    user = random.choice(list(nonprofit_state.keys()))
                    target = random.choice(list(nonprofit_state.keys()))
                    result = donate(user, target, amount)

                    if nonprofit_state[user]['balance'] - amount >= 0:
                        assert 'errors' not in result
                        nonprofit_state[user]['balance'] -= amount
                        nonprofit_state[user]['donated'] += amount
                        nonprofit_state[target]['balance'] += amount
                        nonprofit_state[target]['fundraised'] += amount
                    else:
                        assert 'errors' in result

            elif choice == transact:
                if random.random() < 0.8:  # person transacts
                    user = random.choice(list(person_state.keys()))
                    target = random.choice(list(person_state.keys()))
                    result = transact(user, target, amount)

                    if person_state[user]['balance'] - amount >= 0:
                        assert 'errors' not in result
                        person_state[user]['balance'] -= amount
                        person_state[target]['balance'] += amount
                    else:
                        assert 'errors' in result
                else:  # nonprofit transacts
                    user = random.choice(list(nonprofit_state.keys()))
                    target = random.choice(list(person_state.keys()))
                    result = transact(user, target, amount)

                    if nonprofit_state[user]['balance'] - amount >= 0:
                        assert 'errors' not in result
                        nonprofit_state[user]['balance'] -= amount
                        person_state[target]['balance'] += amount
                    else:
                        assert 'errors' in result

            if choice == withdraw:
                user = random.choice(list(nonprofit_state.keys()))
                result = withdraw(user, amount)

                if nonprofit_state[user]['balance'] - amount >= 0:
                    assert 'errors' not in result
                    nonprofit_state[user]['balance'] -= amount
                else:
                    assert 'errors' in result

        for x in person_state:
            assert person_state[x]['balance'] == x.balance()
            assert person_state[x]['donated'] == x.donated()

        for x in nonprofit_state:
            assert nonprofit_state[x]['balance'] == x.balance()
            assert nonprofit_state[x]['fundraised'] == x.fundraised()

    # test notifications, especially deduping behavior
    def test_notifications(self):
        def create_operation(op_name):
            variables = {'user': self.me_person.gid}
            types = {}

            if op_name == 'FollowCreate':
                variables['target'] = self.person.gid
            elif op_name == 'LikeCreate':
                variables['target'] = to_global_id(
                    'DonationNode',
                    models.Donation.objects.filter(
                        user=self.person).first().id)
            elif op_name == 'TransactionCreate':
                variables['description'] = 'description'
                variables['target'] = self.person.gid
                variables['amount'] = 1
            elif op_name == 'CommentCreate':
                variables['description'] = 'description'
                variables['parent'] = to_global_id(
                    'DonationNode',
                    models.Donation.objects.filter(
                        user=self.person).first().id,
                )
                variables['self'] = self.me_person.gid
            elif op_name == 'NewsCreate':
                variables['description'] = 'description'
                variables['title'] = 'title'
                variables['link'] = 'link'
                variables['image'] = 'image'
            elif op_name == 'EventCreate':
                variables['description'] = 'description'
                variables['title'] = 'title'
                variables['link'] = 'link'
                variables['image'] = 'image'
                variables['date'] = str(now())
                variables['duration'] = 60
                variables['address'] = 'address'
                types['duration'] = 'Int!'
            elif op_name == 'PostCreate':
                variables['description'] = 'description'
                variables['title'] = 'title'
            else:
                raise KeyError

            try:
                query = self.gql[op_name]
            except KeyError:
                # this must be a nonprofit-only action (news or event)
                variables = {x: variables[x] for x in variables if x != 'user'}
                query = '''
                    mutation {op_name}($user: ID! {vt}) {{
                        create{op_type}(user: $user {vm}) {{
                            {op_lower} {{
                                id
                            }}
                        }}
                    }}
                '''.format(
                    op_name=op_name,
                    op_type=op_name.replace('Create', ''),
                    op_lower=op_name.replace('Create', '').lower(),
                    vt=' '.join('${}: {}'.format(
                        x, types[x] if x in types else 'String!')
                                for x in variables),
                    vm=' '.join('{}: ${}'.format(x, x) for x in variables),
                )
                variables['user'] = self.nonprofit.gid

            self._client.force_login(self.staff)
            result = json.loads(
                self.query(
                    query,
                    op_name=op_name,
                    variables=variables,
                ).content)
            self._client.force_login(self.person)
            assert 'errors' not in result
            try:
                return list(list(result['data'].values())[0].values())[0]['id']
            except TypeError:
                return variables['target']

        def delete_operation(op_name, id):
            if op_name in ['FollowDelete', 'LikeDelete']:
                query = self.gql[op_name]
                variables = {'user': self.me_person.gid, 'target': id}
            else:
                query = '''
                    mutation {}($id: ID!) {{
                        delete{}(id: $id) {{
                            status
                        }}
                    }}
                '''.format(op_name, op_name.replace('Delete', ''))
                variables = {'id': id}

            self._client.force_login(self.staff)
            result = json.loads(
                self.query(
                    query,
                    op_name=op_name,
                    variables=variables,
                ).content)
            self._client.force_login(self.person)
            assert 'errors' not in result

        def query_unseen():
            self._client.force_login(self.person)
            result = json.loads(
                self.query(
                    self.gql['Notifier'],
                    op_name='Notifier',
                    variables={
                        'id': to_global_id('IbisUserNode', self.person.id),
                    },
                ).content)
            assert 'errors' not in result
            return result['data']['ibisUser']['notifier']['unseenCount']

        self.person.notifier.email_follow = True
        self.person.notifier.email_transaction = True
        self.person.notifier.email_comment = True
        self.person.notifier.email_like = True

        self.person.notifier.save()

        count = self.person.notifier.notification_set.all().count()

        models.Deposit.objects.create(
            user=self.me_person,
            amount=200,
            payment_id='unique_test_notifications',
        )

        self.person.following.add(self.nonprofit)
        self.person.following.add(self.me_person)

        def run(op_type, c):
            id = create_operation('{}Create'.format(op_type))
            assert self.person.notifier.notification_set.all().count() == c + 1
            delete_operation('{}Delete'.format(op_type), id)
            assert self.person.notifier.notification_set.all().count() == c + 0
            create_operation('{}Create'.format(op_type))
            assert self.person.notifier.notification_set.all().count() == c + 1

        run('Follow', count)
        run('Follow', count)
        run('Like', count + 1)
        run('Like', count + 1)
        run('Transaction', count + 2)
        run('Transaction', count + 3)
        run('Comment', count + 4)
        run('Comment', count + 5)
        run('News', count + 6)
        run('News', count + 7)
        run('Event', count + 8)
        run('Event', count + 9)
        run('Post', count + 10)
        run('Post', count + 11)

        assert query_unseen() == count + 12

        self._client.force_login(self.person)
        assert 'errors' not in json.loads(
            self.query(
                self.gql['CommentCreate'],
                op_name='CommentCreate',
                variables={
                    'user':
                    self.person.gid,
                    'parent':
                    to_global_id(
                        'DonationNode',
                        models.Donation.objects.filter(
                            user=self.person).first().id,
                    ),
                    'description':
                    'This is a description',
                    'self':
                    self.person.gid,
                },
            ).content)
        assert self.person.notifier.notification_set.all().count(
        ) == count + 12

        self._client.force_login(self.person)
        assert 'errors' not in json.loads(
            self.query(
                self.gql['NotifierSeen'],
                op_name='NotifierSeen',
                variables={
                    'id': to_global_id('NotifierNode', self.person.id),
                    'lastSeen': str(now()),
                },
            ).content)
        assert query_unseen() == 0

        follow_id = create_operation('FollowCreate')
        like_id = create_operation('LikeCreate')
        delete_operation('FollowDelete', follow_id)
        delete_operation('LikeDelete', like_id)
        follow_id = create_operation('FollowCreate')
        like_id = create_operation('LikeCreate')
        assert query_unseen() == 2

        delete_operation('FollowDelete', follow_id)
        delete_operation('LikeDelete', like_id)
        assert query_unseen() == 0

    # makes sure the username validator + valid generator works as expected
    def test_usernames(self):
        for user in models.IbisUser.objects.all():
            assert len(user.username) <= models.MAX_USERNAME_LEN
            assert len(user.username) >= models.MIN_USERNAME_LEN
            assert re.sub(r'\W+', '', user.username) == user.username

        person = models.Person.objects.create(
            username='This is an INVALID @username',
            email='invalid@example.com',
            first_name='John',
            last_name='Invalid',
        )
        try:
            person.clean()
            raise AssertionError
        except ValidationError:
            pass

        person1 = models.Person.objects.create(
            username=models.generate_valid_username('Jane', 'Valid'),
            email='invalid@example.com',
            first_name='Jane',
            last_name='Valid',
        )

        assert person1.username == 'jane_valid'

        person2 = models.Person.objects.create(
            username=models.generate_valid_username('Jane', 'Valid'),
            email='invalid@example.com',
            first_name='Jane',
            last_name='Valid',
        )

        assert person2.username == 'jane_valid_2'
