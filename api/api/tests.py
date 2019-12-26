import os
import json
import logging
from django.core.management import call_command
from graphene_django.utils.testing import GraphQLTestCase
from graphql_relay.node.node import to_global_id
from django.utils.timezone import now, timedelta

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
    fixtures = ['fixtures.json']
    operations = [
        'BookmarkCreate',
        'BookmarkDelete',
        'CommentCreate',
        'CommentTree',
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
        self.assertCountEqual(self.gql.keys(), self.operations)
        assert len(models.Person.objects.all()) == NUM_PERSON
        assert len(models.Donation.objects.all()) == NUM_DONATION
        assert len(models.Transaction.objects.all()) == NUM_TRANSACTION
        assert len(models.News.objects.all()) == NUM_NEWS
        assert len(models.Event.objects.all()) == NUM_EVENT
        assert len(models.Post.objects.all()) == NUM_POST
        assert len(models.Comment.objects.all()) == NUM_COMMENT

        self.person_state = {}
        for x in models.Person.objects.all():
            self.person_state[x] = {
                'balance': x.balance(),
                'donated': x.donated(),
                'following': list(x.following.all()),
                'bookmark_for_news': list(x.bookmark_for_news.all()),
                'bookmark_for_post': list(x.bookmark_for_post.all()),
                'rsvp_for_event': list(x.rsvp_for_event.all()),
                'likes_donation': list(x.following.all()),
                'likes_transaction': list(x.likes_transaction.all()),
                'likes_news': list(x.likes_news.all()),
                'likes_event': list(x.likes_event.all()),
                'likes_post': list(x.likes_post.all()),
                'likes_comment': list(x.likes_comment.all()),
            }

        self.nonprofit_state = {}
        for x in models.Nonprofit.objects.all():
            self.person_state[x] = {
                'balance': x.balance(),
                'fundraised': x.fundraised(),
            }

        self.me = models.Person.objects.create(
            username='user',
            password='password',
            first_name='User',
            last_name='McUserFace',
            email='user@example.com',
        )

        models.Deposit.objects.create(
            user=self.me,
            amount=300,
            payment_id='unique',
        )

        self.nonprofit = models.Nonprofit.objects.all().first()
        self.person = models.Person.objects.all().first()
        self.donation = models.Donation.objects.all().first()
        self.transaction = models.Transaction.objects.all().first()
        self.news = models.News.objects.all().first()
        self.event = models.Event.objects.all().first()
        self.post = models.Post.objects.all().first()

        self.me.gid = to_global_id('PersonNode', self.me.id)
        self.nonprofit.gid = to_global_id('NonprofitNode', self.nonprofit.id)
        self.person.gid = to_global_id('PersonNode', self.person.id)
        self.donation.gid = to_global_id('DonationNode', self.donation.id)
        self.transaction.gid = to_global_id('TransactionNode',
                                            self.transaction.id)
        self.news.gid = to_global_id('NewsNode', self.news.id)
        self.event.gid = to_global_id('EventNode', self.event.id)
        self.post.gid = to_global_id('PostNode', self.post.id)

        # make sure that self.me and self.person both have one notification
        donation_me = models.Donation.objects.create(
            user=self.me,
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
                'target': to_global_id('DonationNode', donation_me.id),
            },
        )
        self._client.logout()
        self._client.force_login(self.me)
        self.query(
            self.gql['LikeCreate'],
            op_name='LikeCreate',
            variables={
                'user': self.me.gid,
                'target': to_global_id('DonationNode', donation_person.id),
            },
        )
        self._client.logout()

        self.notification = self.me.notifier.notification_set.first()

    def query(self, query, op_name=None, variables=None):
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

    # staff can do everything
    def run_all(self, person):
        success = {}
        init_tracker_len = len(tracker.models.Log.objects.all())

        result = json.loads(
            self.query(
                self.gql['DonationCreate'],
                op_name='DonationCreate',
                variables={
                    'user': person.gid,
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
                    'user': person.gid,
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
                    'user': person.gid,
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
                    'user': person.gid,
                    'parent': self.donation.gid,
                    'description': 'This is a description',
                    'self': person.gid,
                },
            ).content)
        success['CommentCreate'] = 'errors' not in result and result['data'][
            'createComment']['comment']['id']

        result = json.loads(
            self.query(
                self.gql['FollowCreate'],
                op_name='FollowCreate',
                variables={
                    'user': person.gid,
                    'target': self.person.gid,
                },
            ).content)
        success['FollowCreate'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['LikeCreate'],
                op_name='LikeCreate',
                variables={
                    'user': person.gid,
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
                    'user': person.gid,
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
                    'user': person.gid,
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
                    'id': person.gid,
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
                    'id': person.gid,
                },
            ).content)
        success['Home'] = 'errors' not in result and bool(
            result['data']['person']['id'])

        result = json.loads(
            self.query(
                self.gql['SideMenu'],
                op_name='SideMenu',
                variables={
                    'id': person.gid,
                },
            ).content)
        success['SideMenu'] = 'errors' not in result and bool(
            result['data']['person']['id'])

        result = json.loads(
            self.query(
                self.gql['Settings'],
                op_name='Settings',
                variables={
                    'id': person.gid,
                },
            ).content)
        success['Settings'] = 'errors' not in result and bool(
            result['data']['person']['notifier']['id'])

        result = json.loads(
            self.query(
                self.gql['Notifier'],
                op_name='Notifier',
                variables={
                    'id': person.gid,
                },
            ).content)
        success['Notifier'] = 'errors' not in result and (
            result['data']['person']['notifier']['id'] == to_global_id(
                'NotifierNode', person.id))

        result = json.loads(
            self.query(
                self.gql['NonprofitList'],
                op_name='NonprofitList',
                variables={
                    'self': person.gid,
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
                    'self': person.gid,
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
                    'self': person.gid,
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
                    'self': person.gid,
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
                    'self': person.gid,
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
                    'self': person.gid,
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
                    'self': person.gid,
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
                    'self': person.gid,
                },
            ).content)
        success['CommentTree'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['DepositList'],
                op_name='DepositList',
                variables={
                    'byUser': person.gid,
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
                    'forUser': person.gid,
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
                    'user': person.gid,
                    'target': self.donation.gid,
                },
            ).content)
        success['LikeDelete'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['FollowDelete'],
                op_name='FollowDelete',
                variables={
                    'user': person.gid,
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
                    'user': person.gid,
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
                    'user': person.gid,
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
                    'id': person.gid,
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
                    'id': person.gid,
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
                    'id': person.gid,
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
                    'id': person.gid,
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
                    'id': to_global_id('NotifierNode', person.id),
                    'lastSeen': str(now()),
                },
            ).content)
        success['NotifierSeen'] = 'errors' not in result and result['data'][
            'updateNotifier']['notifier']['id']

        notification = person.notifier.notification_set.first()

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

    # --- Permissions ------------------------------------------------------- #

    # staff can do everything
    def test_staff(self):
        staff = users.models.User.objects.create(
            username='staff',
            first_name='Staffy',
            last_name='McStaffface',
            email='staff@example.come',
            is_staff=True,
        )
        self._client.force_login(staff)
        assert all(self.run_all(self.me).values())

    # anonymous users can't do anything
    def test_anonymous(self):
        assert not any(self.run_all(self.me).values())

    # logged in users can see all of their own information
    def test_self(self):
        self._client.force_login(self.me)
        assert all(self.run_all(self.me).values())

    # logged in users can see some of other people's information
    def test_other_public(self):
        self._client.force_login(self.me)
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
        result = self.run_all(self.person)
        assert(result[x] == expected[x] for x in result)
