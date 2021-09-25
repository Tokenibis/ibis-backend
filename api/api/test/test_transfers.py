import json
import random
import ibis.models as models

from django.conf import settings
from graphql_relay.node.node import to_global_id
from api.test.base import BaseTestCase


class TransferTestCase(BaseTestCase):
    # make sure that money constraints work
    def test_transfer_limits(self):
        def donate(target, amount):
            return 'errors' not in json.loads(
                self.query(
                    self.gql['DonationCreate'],
                    op_name='DonationCreate',
                    variables={
                        'user': self.me_person.gid,
                        'target': target.gid,
                        'amount': amount,
                        'description': 'This is a description',
                    },
                ).content)

        def reward(target, amount):
            return 'errors' not in json.loads(
                self.query(
                    self.gql['RewardCreate'],
                    op_name='RewardCreate',
                    variables={
                        'user': self.me_bot.gid,
                        'target': target.gid,
                        'amount': amount,
                        'description': 'This is a description',
                    },
                ).content)

        self.me_person.deposit_set.all().delete()

        models.Deposit.objects.create(
            user=self.me_person,
            amount=int(
                (settings.MAX_TRANSFER - self.me_person.balance()) * 1.5),
            description='unique_test_transfer_limit_donation',
            category=models.ExchangeCategory.objects.first(),
        )

        self._client.force_login(self.me_person)

        assert not donate(self.organization, -1)
        assert not donate(self.organization, 0.5)
        assert not donate(self.organization, 0)
        assert not donate(self.organization, settings.MAX_TRANSFER + 1)
        assert donate(self.organization, settings.MAX_TRANSFER)
        assert donate(self.organization, self.me_person.balance())
        assert not donate(self.organization, 1)

        models.Deposit.objects.create(
            user=self.me_bot,
            amount=int((settings.MAX_TRANSFER - self.me_bot.balance()) * 1.5),
            description='unique_test_transfer_limit_reward',
            category=models.ExchangeCategory.objects.first(),
        )

        self._client.force_login(self.me_bot)

        assert not reward(self.person, -1)
        assert not reward(self.person, 0.5)
        assert not reward(self.person, 0)
        assert reward(self.person, settings.MAX_TRANSFER)
        assert reward(self.person, self.me_bot.balance())
        assert not reward(self.person, 1)

    # send money around randomly and make sure that balances agree at the end
    def test_transfer_dynamic(self):
        def deposit(user, amount):
            models.Deposit.objects.create(
                user=user,
                amount=amount,
                description='unique_{}_{}'.format(
                    user.username,
                    len(user.deposit_set.all()),
                ),
                category=models.ExchangeCategory.objects.first(),
            )
            return '{"success": true}'

        def donate(user, target, amount):
            self._client.force_login(user)
            result = json.loads(
                self.query(
                    self.gql['DonationCreate'],
                    op_name='DonationCreate',
                    variables={
                        'user': to_global_id('UserNode', user.id),
                        'target': to_global_id('UserNode', target.id),
                        'amount': amount,
                        'description': 'This is a donation',
                    },
                ).content)
            self._client.logout()
            return result

        def reward(user, target, amount):
            self._client.force_login(user)
            result = json.loads(
                self.query(
                    self.gql['RewardCreate'],
                    op_name='RewardCreate',
                    variables={
                        'user': to_global_id('UserNode', user.id),
                        'target': to_global_id('UserNode', target.id),
                        'amount': amount,
                        'description': 'This is a reward',
                    },
                ).content)
            self._client.logout()
            return result

        def withdraw(user, amount):
            if user.balance() - amount >= 0:
                models.Withdrawal.objects.create(
                    user=user,
                    amount=amount,
                    category=models.ExchangeCategory.objects.first(),
                )
                return True
            else:
                return False

        person_state = {
            x: {
                'balance': x.balance(),
                'donated': x.donated(),
            }
            for x in models.Person.objects.all()
        }

        organization_state = {
            x: {
                'balance': x.balance(),
                'fundraised': x.fundraised(),
            }
            for x in models.Organization.objects.all()
        }

        bot_state = {
            x: {
                'balance': x.balance(),
            }
            for x in models.Bot.objects.all()
        }

        step = sum(person_state[x]['balance']
                   for x in person_state) / len(person_state) / 10

        for _ in range(200):
            choice = random.choice([deposit, donate, reward, withdraw])
            amount = random.randint(1, min(step * 2 - 1,
                                           settings.MAX_TRANSFER))

            if choice == deposit:
                user = random.choice(list(person_state.keys()))
                assert 'errors' not in deposit(user, amount)

                person_state[user]['balance'] += amount

            elif choice == donate:
                user = random.choice(list(person_state.keys()))
                target = random.choice(list(organization_state.keys()))
                result = donate(user, target, amount)

                if person_state[user]['balance'] - amount >= 0:
                    assert 'errors' not in result
                    person_state[user]['balance'] -= amount
                    person_state[user]['donated'] += amount
                    organization_state[target]['balance'] += amount
                    organization_state[target]['fundraised'] += amount
                else:
                    assert 'errors' in result

            elif choice == reward:
                user = random.choice(list(bot_state.keys()))
                target = random.choice(list(person_state.keys()))
                result = reward(user, target, amount)

                if bot_state[user]['balance'] - amount >= 0:
                    assert 'errors' not in result
                    bot_state[user]['balance'] -= amount
                    person_state[target]['balance'] += amount
                else:
                    assert 'errors' in result

            if choice == withdraw:
                user = random.choice(list(organization_state.keys()))
                result = withdraw(user, amount)

                if organization_state[user]['balance'] - amount >= 0:
                    assert result
                    organization_state[user]['balance'] -= amount
                else:
                    assert not result

        for x in person_state:
            assert person_state[x]['balance'] == x.balance()
            assert person_state[x]['donated'] == x.donated()

        for x in organization_state:
            assert organization_state[x]['balance'] == x.balance()
            assert organization_state[x]['fundraised'] == x.fundraised()

        for x in bot_state:
            assert bot_state[x]['balance'] == x.balance()
