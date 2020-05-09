import re
import json
import tracker.models
import ibis.models as models

from django.core.exceptions import ValidationError
from django.utils.timezone import now, timedelta
from graphql_relay.node.node import to_global_id
from api.test.base import BaseTestCase


class PermissionTestCase(BaseTestCase):
    def run_all(self, user):
        success = {}
        init_tracker_len = len(tracker.models.Log.objects.all())

        result = json.loads(
            self.query(
                self.gql['Balance'],
                op_name='Balance',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                },
            ).content)
        success['Balance'] = 'errors' not in result and bool(
            result['data']['ibisUser']['id'])

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
                self.gql['NewsCreate'],
                op_name='NewsCreate',
                variables={
                    'user': user.gid,
                    'title': 'This is a title',
                    'image': 'This is an image',
                    'link': 'This is a link',
                    'description': 'This is a description',
                },
            ).content)
        success['NewsCreate'] = 'errors' not in result and result['data'][
            'createNews']['news']['id']

        result = json.loads(
            self.query(
                self.gql['NewsUpdate'],
                op_name='NewsUpdate',
                variables={
                    'id': to_global_id(
                        'NewsNode',
                        models.News.objects.last().id,
                    ),
                    'user': user.gid,
                    'title': 'This is a different title',
                    'image': 'This is a different image',
                    'link': 'This is a different link',
                    'description': 'This is a different description',
                },
            ).content)
        success['NewsUpdate'] = 'errors' not in result and result['data'][
            'updateNews']['news']['id']

        result = json.loads(
            self.query(
                self.gql['EventCreate'],
                op_name='EventCreate',
                variables={
                    'user': user.gid,
                    'title': 'This is a title',
                    'image': 'This is an image',
                    'link': 'This is a link',
                    'description': 'This is a description',
                    'address': 'This is an address',
                    'date': str(now()),
                    'duration': 1,
                },
            ).content)
        success['EventCreate'] = 'errors' not in result and result['data'][
            'createEvent']['event']['id']

        result = json.loads(
            self.query(
                self.gql['EventUpdate'],
                op_name='EventUpdate',
                variables={
                    'id':
                    to_global_id(
                        'EventNode',
                        models.Event.objects.last().id,
                    ),
                    'user':
                    user.gid,
                    'title':
                    'This is a different title',
                    'image':
                    'This is a different image',
                    'link':
                    'This is a different link',
                    'description':
                    'This is a different description',
                    'address':
                    'This is a different address',
                    'date':
                    str(now()),
                    'duration':
                    2,
                },
            ).content)
        success['EventUpdate'] = 'errors' not in result and result['data'][
            'updateEvent']['event']['id']

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
                    'id': self.person.gid,
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
                self.gql['IbisUserList'],
                op_name='IbisUserList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['IbisUserList'] = 'errors' not in result and len(
            result['data']['allIbisUsers']['edges']) > 0

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
                self.gql['NonprofitSettingsUpdate'],
                op_name='NonprofitSettingsUpdate',
                variables={
                    'id': self.me_nonprofit.gid,
                    'visibilityDonation': models.IbisUser.PUBLIC,
                    'visibilityTransaction': models.IbisUser.PUBLIC,
                },
            ).content)
        success['NonprofitSettingsUpdate'] = 'errors' not in result and result[
            'data']['updateNonprofit']['nonprofit']['id']

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
                    'id': self.me_person.gid,
                    'visibilityDonation': models.IbisUser.PUBLIC,
                    'visibilityTransaction': models.IbisUser.PUBLIC,
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

        result = json.loads(
            self.query(
                self.gql['WithdrawalList'],
                op_name='WithdrawalList',
                variables={
                    'byUser': self.me_nonprofit.gid,
                    'orderBy': '-created',
                    'first': 25,
                },
            ).content)
        success['WithdrawalList'] = 'errors' not in result and bool(
            len(result['data']['allWithdrawals']['edges']) > 0)

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
        expected_fail = [
            'NonprofitSettingsUpdate',
            'NewsCreate',
            'NewsUpdate',
            'EventCreate',
            'EventUpdate',
            'WithdrawalList',
        ]
        self._client.force_login(self.me_person)
        results = self.run_all(self.me_person)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

    # logged in users can see all of their own information
    def test_nonprofit(self):
        expected_fail = [
            'PersonSettingsUpdate',
            'PostCreate',
        ]
        self._client.force_login(self.me_nonprofit)
        results = self.run_all(self.me_nonprofit)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

    # logged in users can see some of other people's information
    def test_other_public(self):
        expected = {
            'Balance': True,
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
            'IbisUserList': True,
            'LikeCreate': False,
            'LikeDelete': False,
            'News': True,
            'NewsList': True,
            'Nonprofit': True,
            'NonprofitList': True,
            'NonprofitSettingsUpdate': False,
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

        self.person.visibility_donation = models.IbisUser.PUBLIC
        self.person.visibility_transaction = models.IbisUser.PUBLIC
        self.person.save()

        self._client.force_login(self.me_person)
        result = self.run_all(self.person)
        assert (result[x] == expected[x] for x in result)

    # anyone can see public visibility
    def test_privacy_public(self):
        self.person.visibility_donation = models.IbisUser.PUBLIC
        self.person.visibility_transaction = models.IbisUser.PUBLIC
        self.person.save()

        self._client.force_login(self.me_person)
        assert all(self.run_privacy(self.person).values())

    # nobody can see private visibility except self
    def test_privacy_private(self):
        self.person.visibility_donation = models.IbisUser.PRIVATE
        self.person.visibility_transaction = models.IbisUser.PRIVATE
        self.person.save()

        self._client.force_login(self.me_person)
        assert not any(self.run_privacy(self.person).values())

        self._client.force_login(self.person)
        assert all(self.run_privacy(self.person).values())

    # only people being followed have visibility if set to 'following'
    def test_privacy_following(self):
        self.person.visibility_donation = models.IbisUser.FOLLOWING
        self.person.visibility_transaction = models.IbisUser.FOLLOWING
        self.person.save()

        self._client.force_login(self.me_person)
        assert not any(self.run_privacy(self.person).values())

        self.person.following.add(self.me_person)
        self.person.save()

        self._client.force_login(self.me_person)
        assert all(self.run_privacy(self.person).values())

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
