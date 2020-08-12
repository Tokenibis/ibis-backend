import os
import json
import ibis.models as models

from django.conf import settings
from graphql.language.base import parse
from graphql_relay.node.node import to_global_id
from api.test.base import BaseTestCase

DIR = os.path.dirname(os.path.realpath(__file__))


class BotTestCase(BaseTestCase):
    operations_bot = [
        'Activity',
        'ActivityCreate',
        'ActivityList',
        'ActivityUpdate',
        'Balance',
        'Bot',
        'BotList',
        'BotUpdate',
        'Comment',
        'CommentCreate',
        'CommentList',
        'Donation',
        'DonationList',
        'Event',
        'EventList',
        'FollowCreate',
        'FollowDelete',
        'LikeCreate',
        'LikeDelete',
        'News',
        'NewsList',
        'Organization',
        'OrganizationList',
        'Person',
        'PersonList',
        'Post',
        'PostList',
        'Reward',
        'RewardCreate',
        'RewardList',
        'User',
        'UserList',
    ]

    @classmethod
    def setUpTestData(cls):
        cls.gql_bot = {}
        gql_dir = 'graphql/bot'
        for filename in os.listdir(os.path.join(DIR, gql_dir)):
            if filename.split('.')[-1] == 'gql':
                with open(os.path.join(DIR, gql_dir, filename)) as fd:
                    cls.gql_bot[filename.split('.')[0]] = fd.read()

        super(BotTestCase, cls).setUpTestData()

    def setUp(self):
        super().setUp()

        self.assertCountEqual(self.gql_bot.keys(), self.operations_bot)
        for x in self.gql_bot:
            definition = parse(self.gql_bot[x]).definitions[0]
            if definition.operation != 'query':
                assert definition.selection_set.selections[
                    0].name.value in settings.BOT_GAS_MUTATION

    def run_all(self, user):
        success = {}
        result = json.loads(
            self.query(
                self.gql_bot['Balance'],
                op_name='Balance',
                variables={
                    'id': to_global_id('UserNode', user.id),
                },
            ).content)
        success['Balance'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['Bot'],
                op_name='Bot',
                variables={
                    'id': self.me_bot.gid,
                },
            ).content)
        success['Bot'] = 'errors' not in result and bool(
            result['data']['bot']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['BotList'],
                op_name='BotList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['BotList'] = 'errors' not in result and len(
            result['data']['allBots']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql_bot['BotUpdate'],
                op_name='BotUpdate',
                variables={
                    'id': to_global_id('UserNode', self.me_bot.id),
                    'tank': settings.BOT_GAS_INITIAL + 1,
                },
            ).content)
        success['BotUpdate'] = 'errors' not in result and result['data'][
            'updateBot']['bot']['id']

        result = json.loads(
            self.query(
                self.gql_bot['CommentCreate'],
                op_name='CommentCreate',
                variables={
                    'user': user.gid,
                    'parent': self.donation.gid,
                    'description': 'This is a description',
                },
            ).content)
        success['CommentCreate'] = 'errors' not in result and result['data'][
            'createComment']['comment']['id']

        result = json.loads(
            self.query(
                self.gql_bot['Comment'],
                op_name='Comment',
                variables={
                    'id': result['data']['createComment']['comment']['id'],
                },
            ).content)
        success['Comment'] = 'errors' not in result and bool(
            result['data']['comment']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['CommentList'],
                op_name='CommentList',
                variables={
                    'hasParent': to_global_id('EntryNode', self.donation.id),
                },
            ).content)
        success['CommentList'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql_bot['Donation'],
                op_name='Donation',
                variables={
                    'id': self.donation.gid,
                },
            ).content)
        success['Donation'] = 'errors' not in result and bool(
            result['data']['donation']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['DonationList'],
                op_name='DonationList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['DonationList'] = 'errors' not in result and len(
            result['data']['allDonations']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql_bot['Event'],
                op_name='Event',
                variables={
                    'id': self.event.gid,
                },
            ).content)
        success['Event'] = 'errors' not in result and bool(
            result['data']['event']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['EventList'],
                op_name='EventList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['EventList'] = 'errors' not in result and len(
            result['data']['allEvents']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql_bot['FollowCreate'],
                op_name='FollowCreate',
                variables={
                    'user': user.gid,
                    'target': self.person.gid,
                },
            ).content)
        success['FollowCreate'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql_bot['FollowDelete'],
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
                self.gql_bot['User'],
                op_name='User',
                variables={
                    'id': to_global_id('UserNode', self.person.id),
                },
            ).content)
        success['User'] = 'errors' not in result and bool(
            result['data']['user']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['UserList'],
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
                self.gql_bot['LikeCreate'],
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
                self.gql_bot['LikeDelete'],
                op_name='LikeDelete',
                variables={
                    'user': user.gid,
                    'target': self.donation.gid,
                },
            ).content)
        success['LikeDelete'] = 'errors' not in result and len(result) > 0

        result = json.loads(
            self.query(
                self.gql_bot['News'],
                op_name='News',
                variables={
                    'id': self.news.gid,
                },
            ).content)
        success['News'] = 'errors' not in result and bool(
            result['data']['news']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['NewsList'],
                op_name='NewsList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['NewsList'] = 'errors' not in result and len(
            result['data']['allNews']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql_bot['Organization'],
                op_name='Organization',
                variables={
                    'id': self.organization.gid,
                },
            ).content)
        success['Organization'] = 'errors' not in result and bool(
            result['data']['organization']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['OrganizationList'],
                op_name='OrganizationList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['OrganizationList'] = 'errors' not in result and len(
            result['data']['allOrganizations']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql_bot['Person'],
                op_name='Person',
                variables={
                    'id': self.person.gid,
                },
            ).content)
        success['Person'] = 'errors' not in result and bool(
            result['data']['person']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['PersonList'],
                op_name='PersonList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['PersonList'] = 'errors' not in result and len(
            result['data']['allPeople']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql_bot['Post'],
                op_name='Post',
                variables={
                    'id': self.post.gid,
                },
            ).content)
        success['Post'] = 'errors' not in result and bool(
            result['data']['post']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['PostList'],
                op_name='PostList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['PostList'] = 'errors' not in result and len(
            result['data']['allPosts']['edges']) > 0

        result = json.loads(
            self.query(
                self.gql_bot['Reward'],
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
                self.gql_bot['RewardCreate'],
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
                self.gql_bot['RewardList'],
                op_name='RewardList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['RewardList'] = 'errors' not in result and len(
            result['data']['allRewards']['edges']) > 0

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
                    'rangeMin': 10,
                    'rangeRange': 5,
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
                    'rangeMin':
                    11,
                    'rangeRange':
                    6,
                },
            ).content)
        success['ActivityUpdate'] = 'errors' not in result and result['data'][
            'updateActivity']['activity']['id']

        return success

    # staff can do everything
    def test_staff(self):
        self._client.force_login(self.staff)
        assert all(self.run_all(self.me_bot).values())

    # bots can do everything
    def test_bot(self):
        self._client.force_login(self.me_bot)
        assert all(self.run_all(self.me_bot).values())

    # TODO: test that the metering deduction works as advertised
