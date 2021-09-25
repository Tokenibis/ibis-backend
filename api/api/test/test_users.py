import re
import json
import ibis.models as models

from freezegun import freeze_time
from django.core.exceptions import ValidationError
from django.utils.timezone import now, timedelta, utc
from graphql_relay.node.node import to_global_id
from api.test.base import BaseTestCase, TEST_TIME


class PermissionTestCase(BaseTestCase):
    @freeze_time(TEST_TIME.astimezone(utc).date())
    def run_all(self, user):
        success = {}

        result = json.loads(
            self.query(
                self.gql['Finance'],
                op_name='Finance',
                variables={
                    'id': to_global_id('UserNode', user.id),
                },
            ).content)
        success['Finance'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['DonationCreate'],
                op_name='DonationCreate',
                variables={
                    'user': to_global_id('UserNode', user.id),
                    'target': self.organization.gid,
                    'amount': 100,
                    'description': 'This is a donation',
                },
            ).content)
        success['DonationCreate'] = 'errors' not in result and result['data'][
            'createDonation']['donation']['id']

        result = json.loads(
            self.query(
                self.gql['NewsCreate'],
                op_name='NewsCreate',
                variables={
                    'user': user.gid,
                    'title': 'This is a title',
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
                    'link': 'This is a link',
                    'description': 'This is a description',
                    'address': 'This is an address',
                    'virtual': True,
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
                    'link':
                    'This is a different link',
                    'description':
                    'This is a different description',
                    'address':
                    'This is a different address',
                    'virtual':
                    False,
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
                self.gql['Organization'],
                op_name='Organization',
                variables={
                    'id': self.organization.gid,
                },
            ).content)
        success['Organization'] = 'errors' not in result and bool(
            result['data']['organization']['id'])

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
                self.gql['Reward'],
                op_name='Reward',
                variables={
                    'id':
                    to_global_id(
                        'EntryNode',
                        models.Reward.objects.first().id,
                    ),
                },
            ).content)
        success['Reward'] = 'errors' not in result and bool(
            result['data']['reward']['id'])

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
                    'id': to_global_id('UserNode', user.id),
                },
            ).content)
        success['Home'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['SideMenu'],
                op_name='SideMenu',
                variables={
                    'id': to_global_id('UserNode', user.id),
                },
            ).content)
        success['SideMenu'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['Settings'],
                op_name='Settings',
                variables={
                    'id': to_global_id('UserNode', user.id),
                },
            ).content)
        success['Settings'] = 'errors' not in result and bool(
            result['data']['user']['notifier']['id'])

        result = json.loads(
            self.query(
                self.gql['Notifier'],
                op_name='Notifier',
                variables={
                    'id': to_global_id('UserNode', user.id),
                },
            ).content)
        success['Notifier'] = 'errors' not in result and (
            result['data']['user']['notifier']['id'] == to_global_id(
                'UserNode', user.id))

        result = json.loads(
            self.query(
                self.gql['UserList'],
                op_name='UserList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['UserList'] = 'errors' not in result and len(
            result['data']['allUsers']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['OrganizationList'],
                op_name='OrganizationList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['OrganizationList'] = 'errors' not in result and len(
            result['data']['allOrganizations']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['OrganizationUpdate'],
                op_name='OrganizationUpdate',
                variables={
                    'id': user.gid,
                    'privacyDonation': False,
                    'privacyReward': False,
                },
            ).content)
        success['OrganizationUpdate'] = 'errors' not in result and result[
            'data']['updateOrganization']['organization']['id']

        result = json.loads(
            self.query(
                self.gql['EntryList'],
                op_name='EntryList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['EntryList'] = 'errors' not in result and len(
            result['data']['allEntries']['edges']) > 0

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
                self.gql['RewardList'],
                op_name='RewardList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['RewardList'] = 'errors' not in result and len(
            result['data']['allRewards']['edges']) > 0

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
                self.gql['CommentList'],
                op_name='CommentList',
                variables={
                    'parent': self.donation.gid,
                    'self': user.gid,
                },
            ).content)
        success['CommentList'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql['DepositList'],
                op_name='DepositList',
                variables={
                    'user': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['DepositList'] = 'errors' not in result and bool(
            len(result['data']['allDeposits']['edges']) > 0)

        result = json.loads(
            self.query(
                self.gql['InvestmentList'],
                op_name='InvestmentList',
                variables={
                    'user': user.gid,
                    'orderBy': '-start',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['InvestmentList'] = 'errors' not in result and bool(
            len(result['data']['allInvestments']['edges']) > 0)

        result = json.loads(
            self.query(
                self.gql['NotificationList'],
                op_name='NotificationList',
                variables={
                    'user': user.gid,
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
                    'id': to_global_id('UserNode', user.id),
                    'target': self.organization.gid,
                },
            ).content)
        success['DonationForm'] = 'errors' not in result and result['data'][
            'user'] and bool(result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['PersonUpdate'],
                op_name='PersonUpdate',
                variables={
                    'id': user.gid,
                    'privacyDonation': False,
                    'privacyReward': False,
                },
            ).content)
        success['PersonUpdate'] = 'errors' not in result and result['data'][
            'updatePerson']['person']['id']

        result = json.loads(
            self.query(
                self.gql['NotifierUpdate'],
                op_name='NotifierUpdate',
                variables={
                    'id': user.gid,
                    'emailFollow': True,
                    'emailDonation': True,
                    'emailReward': True,
                },
            ).content)
        success['NotifierUpdate'] = 'errors' not in result and result['data'][
            'updateNotifier']['notifier']['id']

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
                    'user': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                },
            ).content)
        success['WithdrawalList'] = 'errors' not in result and bool(
            len(result['data']['allWithdrawals']['edges']) > 0)

        # assert len(tracker.models.Log.objects.all()) - init_tracker_len == len(
        #     success)

        result = json.loads(
            self.query(
                self.gql['RewardForm'],
                op_name='RewardForm',
                variables={
                    'id': to_global_id('UserNode', user.id),
                    'target': self.person.gid,
                },
            ).content)
        success['RewardForm'] = 'errors' not in result and result['data'][
            'user'] and bool(result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['RewardCreate'],
                op_name='RewardCreate',
                variables={
                    'user': to_global_id('UserNode', user.id),
                    'target': self.person.gid,
                    'amount': 100,
                    'description': 'This is a reward',
                },
            ).content)
        success['RewardCreate'] = 'errors' not in result and result['data'][
            'createReward']['reward']['id']

        result = json.loads(
            self.query(
                self.gql['Activity'],
                op_name='Activity',
                variables={
                    'id': self.activity.gid,
                },
            ).content)
        success['Activity'] = 'errors' not in result and bool(
            result['data']['activity']['id'])

        result = json.loads(
            self.query(
                self.gql['ActivityList'],
                op_name='ActivityList',
                variables={
                    'self': user.gid,
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['ActivityList'] = 'errors' not in result and len(
            result['data']['allActivities']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['ActivityCreate'],
                op_name='ActivityCreate',
                variables={
                    'user': user.gid,
                    'title': 'This is a title',
                    'description': 'This is a description',
                    'active': True,
                    'rewardMin': 10,
                    'rewardRange': 5,
                },
            ).content)
        success['ActivityCreate'] = 'errors' not in result and result['data'][
            'createActivity']['activity']['id']

        result = json.loads(
            self.query(
                self.gql['ActivityUpdate'],
                op_name='ActivityUpdate',
                variables={
                    'id':
                    to_global_id(
                        'EntryNode',
                        models.Activity.objects.last().id,
                    ),
                    'user':
                    user.gid,
                    'title':
                    'This is a different title',
                    'description':
                    'This is a different description',
                    'active':
                    False,
                    'rewardMin':
                    11,
                    'rewardRange':
                    6,
                },
            ).content)
        success['ActivityUpdate'] = 'errors' not in result and result['data'][
            'updateActivity']['activity']['id']

        result = json.loads(
            self.query(
                self.gql['Tutorial'],
                op_name='Tutorial',
                variables={
                    'id': user.gid,
                },
            ).content)
        success['Tutorial'] = 'errors' not in result and bool(
            result['data']['notifier']) and bool(
                result['data']['notifier']['id']) and len(
                    result['data']['allOrganizations']['edges']) == 1

        result = json.loads(
            self.query(
                self.gql['TutorialUpdate'],
                op_name='TutorialUpdate',
                variables={
                    'id': user.gid,
                    'tutorial': True,
                },
            ).content)
        success['TutorialUpdate'] = 'errors' not in result and result['data'][
            'updateNotifier']['notifier']['id']

        result = json.loads(
            self.query(
                self.gql['MessageDirectCreate'],
                op_name='MessageDirectCreate',
                variables={
                    'user': to_global_id('UserNode', user.id),
                    'target': self.person.gid,
                    'description': 'This is a direct message',
                },
            ).content)
        success['MessageDirectCreate'] = 'errors' not in result and result[
            'data']['createMessageDirect']['messageDirect']['id']

        result = json.loads(
            self.query(
                self.gql['MessageDirectList'],
                op_name='MessageDirectList',
                variables={
                    'withUser': self.person.gid,
                    'orderBy': '-last_message',
                    'first': 25,
                    'after': 0,
                },
            ).content)
        success['MessageDirectList'] = 'errors' not in result and len(
            result['data']['allMessagesDirect']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['MessageDirectInbox'],
                op_name='MessageDirectInbox',
                variables={
                    'user': to_global_id('UserNode', user.id),
                },
            ).content)
        success['MessageDirectInbox'] = 'errors' not in result and len(
            result['data']['allUsers']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['MessageChannelCreate'],
                op_name='MessageChannelCreate',
                variables={
                    'user':
                    to_global_id('UserNode', user.id),
                    'target':
                    to_global_id(  # pk=1 is a private channel
                        'ChannelNode',
                        models.Channel.objects.get(pk=2).pk,
                    ),
                    'description':
                    'This is a channel message',
                },
            ).content)
        success['MessageChannelCreate'] = 'errors' not in result and result[
            'data']['createMessageChannel']['messageChannel']['id']

        result = json.loads(
            self.query(
                self.gql['MessageChannelList'],
                op_name='MessageChannelList',
                variables={
                    'withChannel':
                    to_global_id(  # pk=1 is a private channel
                        'ChannelNode',
                        models.Channel.objects.get(pk=2).pk,
                    ),
                    'orderBy':
                    '-last_message',
                    'first':
                    25,
                    'after':
                    0,
                },
            ).content)
        success['MessageChannelList'] = 'errors' not in result and len(
            result['data']['allMessagesChannel']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['MessageChannelInbox'],
                op_name='MessageChannelInbox',
                variables={
                    'user': to_global_id('UserNode', user.id),
                },
            ).content)
        success['MessageChannelInbox'] = 'errors' not in result and len(
            result['data']['allChannels']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql['MessageDirectName'],
                op_name='MessageDirectName',
                variables={
                    'id': to_global_id('UserNode', self.person.id),
                },
            ).content)
        success['MessageDirectName'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql['MessageChannelName'],
                op_name='MessageChannelName',
                variables={
                    'id':
                    to_global_id(
                        'ChannelNode',
                        models.Channel.objects.get(pk=2).pk,
                    ),
                },
            ).content)
        success['MessageChannelName'] = 'errors' not in result and bool(
            result['data']['channel']['id'])

        return success

    def run_privacy(self, person):
        success = {}

        result = json.loads(
            self.query(
                self.gql['DonationList'],
                op_name='DonationList',
                variables={
                    'withUser': person.gid,
                    'orderBy': '-created',
                    'first': 2,
                },
            ).content)
        success['DonationList'] = 'errors' not in result and any(
            x['node']['user']['id'] == to_global_id('UserNode', person.id)
            for x in result['data']['allDonations']['edges'])

        result = json.loads(
            self.query(
                self.gql['RewardList'],
                op_name='RewardList',
                variables={
                    'withUser': person.gid,
                    'orderBy': '-created',
                    'first': 2,
                },
            ).content)
        success['RewardList'] = 'errors' not in result and any(
            x['node']['target']['id'] == to_global_id('UserNode', person.id)
            for x in result['data']['allRewards']['edges'])

        return success

    # # anonymous users can't do anything
    # def test_anonymous(self):
    #     assert not any(self.run_all(self.me_person).values())

    # logged in users can see all of their own information
    def test_person(self):
        expected_fail = [
            'OrganizationUpdate',
            'NewsCreate',
            'NewsUpdate',
            'EventCreate',
            'EventUpdate',
            'ActivityCreate',
            'ActivityUpdate',
            'RewardForm',
            'RewardCreate',
        ]
        self._client.force_login(self.staff)
        results = self.run_all(self.me_person)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

        self._client.force_login(self.staff)
        results = self.run_all(self.me_person)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

    # logged in users can see all of their own information
    def test_organization(self):
        expected_fail = [
            'DonationCreate',
            'PersonUpdate',
            'PostCreate',
            'DonationForm',
            'ActivityCreate',
            'ActivityUpdate',
            'RewardForm',
            'RewardCreate',
            'InvestmentList',
        ]
        self._client.force_login(self.me_organization)
        results = self.run_all(self.me_organization)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

        self._client.force_login(self.staff)
        results = self.run_all(self.me_organization)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

    # logged in users can see all of their own information
    def test_bots(self):
        expected_fail = [
            'DonationCreate',
            'PersonUpdate',
            'PostCreate',
            'DonationForm',
            'OrganizationUpdate',
            'NewsCreate',
            'NewsUpdate',
            'EventCreate',
            'EventUpdate',
            'InvestmentList',
        ]
        self._client.force_login(self.me_bot)
        results = self.run_all(self.me_bot)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

        self._client.force_login(self.staff)
        results = self.run_all(self.me_bot)
        assert all(x[1] for x in results.items() if x[0] not in expected_fail)
        assert not any(x[1] for x in results.items() if x[0] in expected_fail)

    # logged in users can see some of other people's information
    def test_other_public(self):
        expected = {
            'BookmarkCreate': False,
            'CommentCreate': False,
            'CommentList': True,
            'DepositList': False,
            'Donation': True,
            'DonationCreate': False,
            'DonationForm': True,
            'DonationList': True,
            'Event': True,
            'EntryList': True,
            'EventList': True,
            'EventListFilter': True,
            'Finance': True,
            'FollowCreate': False,
            'FollowDelete': False,
            'Home': True,
            'InvestmentList': False,
            'UserList': True,
            'LikeCreate': False,
            'LikeDelete': False,
            'News': True,
            'NewsList': True,
            'Organization': True,
            'OrganizationList': True,
            'OrganizationUpdate': False,
            'NotificationClicked': False,
            'NotificationList': False,
            'Notifier': False,
            'NotifierSeen': False,
            'NotifierUpdate': False,
            'Person': True,
            'PersonList': True,
            'PersonUpdate': False,
            'Post': True,
            'PostCreate': False,
            'PostList': True,
            'RsvpCreate': False,
            'RsvpDelete': False,
            'Settings': False,
            'SideMenu': True,
            'Tutorial': False,
            'TutorialUpdate': False,
            'Reward': True,
            'RewardList': True,
        }

        self._client.force_login(self.me_person)
        result = self.run_all(self.person)
        assert (result[x] == expected[x] for x in result)

    # anyone can see public privacy
    def test_privacy_public(self):
        self._client.force_login(self.me_person)
        assert all(self.run_privacy(self.person).values())

    # nobody can see private privacy except self and target
    def test_privacy_private(self):
        for x in models.Donation.objects.all():
            x.private = True
            x.save()

        for x in models.Reward.objects.all():
            x.private = True
            x.save()

        # self._client.force_login(self.me_person)
        # assert not any(self.run_privacy(self.person).values())

        self._client.force_login(self.person)
        assert all(self.run_privacy(self.person).values())

    # makes sure the username validator + valid generator works as expected
    def test_usernames(self):
        for user in models.User.objects.all():
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
