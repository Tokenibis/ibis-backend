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
        'Balance',
        'BotUpdate',
        'Comment',
        'CommentCreate',
        'CommentList',
        'Donation',
        'DonationCreate',
        'DonationList',
        'Event',
        'EventList',
        'FollowCreate',
        'FollowDelete',
        'IbisUser',
        'IbisUserList',
        'LikeCreate',
        'LikeDelete',
        'News',
        'NewsList',
        'Nonprofit',
        'NonprofitList',
        'Person',
        'PersonList',
        'PersonUpdate',
        'Post',
        'PostCreate',
        'PostList',
        'Transaction',
        'TransactionCreate',
        'TransactionList',
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

        self.bot = models.Bot.objects.create(
            username='bot',
            password='password',
            first_name='Bot',
            last_name='McBotFace',
            email='bot@example.com',
        )
        self.bot.gid = to_global_id('PersonNode', self.bot.id)

        models.Deposit.objects.create(
            user=self.bot,
            amount=300,
            payment_id='unique_bot_1',
            category=models.DepositCategory.objects.first(),
        )

    def run_all(self, user):
        success = {}
        result = json.loads(
            self.query(
                self.gql_bot['Balance'],
                op_name='Balance',
                variables={
                    'id': to_global_id('IbisUserNode', user.id),
                },
            ).content)
        success['Balance'] = 'errors' not in result and bool(
            result['data']['ibisUser']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['BotUpdate'],
                op_name='BotUpdate',
                variables={
                    'id': to_global_id('BotNode', self.bot.id),
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
                self.gql_bot['DonationCreate'],
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
                self.gql_bot['IbisUser'],
                op_name='IbisUser',
                variables={
                    'id': to_global_id('IbisUserNode', self.person.id),
                },
            ).content)
        success['IbisUser'] = 'errors' not in result and bool(
            result['data']['ibisUser']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['IbisUserList'],
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
                self.gql_bot['Nonprofit'],
                op_name='Nonprofit',
                variables={
                    'id': self.nonprofit.gid,
                },
            ).content)
        success['Nonprofit'] = 'errors' not in result and bool(
            result['data']['nonprofit']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['NonprofitList'],
                op_name='NonprofitList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['NonprofitList'] = 'errors' not in result and len(
            result['data']['allNonprofits']['edges']) > 0

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
                self.gql_bot['PersonUpdate'],
                op_name='PersonUpdate',
                variables={
                    'id': self.bot.gid,
                    'description': 'This is a bio',
                },
            ).content)
        success['PersonUpdate'] = 'errors' not in result and result['data'][
            'updatePerson']['person']['id']

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
                self.gql_bot['PostCreate'],
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
                self.gql_bot['Transaction'],
                op_name='Transaction',
                variables={
                    'id': self.transaction.gid,
                },
            ).content)
        success['Transaction'] = 'errors' not in result and bool(
            result['data']['transaction']['id'])

        result = json.loads(
            self.query(
                self.gql_bot['TransactionCreate'],
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
                self.gql_bot['TransactionList'],
                op_name='TransactionList',
                variables={
                    'orderBy': '-created',
                    'first': 25,
                    'after': 1,
                },
            ).content)
        success['TransactionList'] = 'errors' not in result and len(
            result['data']['allTransactions']['edges']) > 0

        return success

    # staff can do everything
    def test_person(self):
        self._client.force_login(self.staff)
        assert all(self.run_all(self.bot).values())

    # bots can do everything
    def test_bot(self):
        self._client.force_login(self.bot)
        assert all(self.run_all(self.bot).values())

    # TODO: test that the metering deduction works as advertised
