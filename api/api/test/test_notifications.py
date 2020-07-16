import json
import ibis.models as models
import notifications.models

from django.core import management
from django.utils.timezone import now, timedelta
from django.conf import settings
from api.test.base import BaseTestCase
from graphql_relay.node.node import to_global_id
from freezegun import freeze_time
from lxml import etree


class NotificationTestCase(BaseTestCase):
    def test_notifications(self):
        def create_operation(op_name, mention=False):
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

            if mention:
                assert 'description' in variables
                variables[
                    'description'] += '\n\n@{}--email@example.com) and @{}'.format(
                        models.Person.objects.exclude(
                            id=self.person.id).first().username,
                        models.Nonprofit.objects.exclude(
                            id=self.nonprofit.id).first().username,
                    )

            query = self.gql[op_name]

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

        def read_last_operation():
            self._client.force_login(self.person)
            reference = self.person.notifier.notification_set.last(
            ).reference.split(':')
            result = json.loads(
                self.query(
                    self.gql[reference[0]],
                    op_name=reference[0],
                    variables={
                        'id': reference[1],
                    }).content)
            assert 'errors' not in result and 'id' in result['data'][
                reference[0][0].lower() + reference[0][1:]]

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

        models.Deposit.objects.create(
            user=self.me_person,
            amount=200,
            payment_id='unique_test_notifications',
            category=models.DepositCategory.objects.first(),
        )

        self.person.following.add(self.nonprofit)
        self.person.following.add(self.me_person)

        def run(op_type, c, mention=False, delete=False):
            id = create_operation('{}Create'.format(op_type), mention)
            assert self.person.notifier.notification_set.count() == c + 1
            if delete:
                delete_operation('{}Delete'.format(op_type), id)
                assert self.person.notifier.notification_set.count() == c + 0
                id = create_operation('{}Create'.format(op_type), mention)
                assert self.person.notifier.notification_set.count() == c + 1
            read_last_operation()

        with freeze_time(now()) as frozen_datetime:
            frozen_datetime.tick(
                delta=timedelta(minutes=settings.EMAIL_DELAY + 2))

            count = self.person.notifier.notification_set.count()
            mention_count = notifications.models.MentionNotification.objects.count(
            )
            email_count = notifications.models.Email.objects.count()

            run('Follow', count, delete=True)
            run('Follow', count, delete=True)
            run('Like', count + 1, delete=True)
            run('Like', count + 1, delete=True)
            run('Transaction', count + 2)
            run('Transaction', count + 3, mention=True)
            run('Comment', count + 4)
            run('Comment', count + 5, mention=True)
            run('News', count + 6)
            run('News', count + 7, mention=True)
            run('Event', count + 8)
            run('Event', count + 9, mention=True)
            run('Post', count + 10)
            run('Post', count + 11, mention=True)

            assert query_unseen() == count + 12

            assert notifications.models.MentionNotification.objects.count(
            ) == mention_count + 10

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
            assert self.person.notifier.notification_set.count() == count + 12

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

            frozen_datetime.tick(delta=timedelta(seconds=1))
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

            assert 'errors' not in json.loads(
                self.query(
                    self.gql['NotificationClicked'],
                    op_name='NotificationClicked',
                    variables={
                        'id':
                        to_global_id(
                            'NotificationNode',
                            list(x for x in
                                 notifications.models.Email.objects.all()
                                 if x.notification.notifier.pk ==
                                 self.person.id)[-1].notification.id,
                        ),
                    },
                ).content)

            # make sure all html emails are well-formed
            for email in notifications.models.Email.objects.all():
                etree.HTML(email.html)

            # make sure we don't spam real email addresses
            assert all(x for x in notifications.models.Email.objects.all()
                       if x.notification.notifier.user.email.split('@')[1] ==
                       'example.com')

            frozen_datetime.tick(delta=timedelta(minutes=settings.EMAIL_DELAY))
            management.call_command('notify')

            # this for loop should have no effect
            for submodel in notifications.models.Notification.__subclasses__():
                for x in submodel.objects.all():
                    x.save()

            assert notifications.models.Email.objects.count(
            ) == email_count + 17
            assert notifications.models.Email.objects.filter(
                status=notifications.models.Email.STALE).count() == email_count
            assert notifications.models.Email.objects.filter(
                status=notifications.models.Email.SUCCEEDED).count() == 16
            assert notifications.models.Email.objects.filter(
                status=notifications.models.Email.UNNEEDED).count() == 1
