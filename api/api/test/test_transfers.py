import json
import random
import ibis.models as models

from django.conf import settings
from graphql_relay.node.node import to_global_id
from api.test.base import BaseTestCase


class TransferTestCase(BaseTestCase):
    # make sure that money constraints work
    def test_transfer_limits(self):
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

        self.me_person.deposit_set.all().delete()

        models.Deposit.objects.create(
            user=self.me_person,
            amount=int(
                (settings.MAX_TRANSFER - self.me_person.balance()) * 1.5),
            payment_id='unique_test_transfer_limit_donation',
            category=models.DepositCategory.objects.first(),
        )

        assert not transfer('DonationCreate', self.organization, -1)
        assert not transfer('DonationCreate', self.organization, 0.5)
        assert not transfer('DonationCreate', self.organization, 0)
        assert not transfer('DonationCreate', self.organization,
                            settings.MAX_TRANSFER + 1)
        assert transfer('DonationCreate', self.organization,
                        settings.MAX_TRANSFER)
        assert transfer('DonationCreate', self.organization,
                        self.me_person.balance())
        assert not transfer('DonationCreate', self.organization, 1)

        models.Deposit.objects.create(
            user=self.me_person,
            amount=int(
                (settings.MAX_TRANSFER - self.me_person.balance()) * 1.5),
            payment_id='unique_test_transfer_limit_transaction',
            category=models.DepositCategory.objects.first(),
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
    def test_transfer_dynamic(self):
        def deposit(user, amount):
            self._client.force_login(self.staff)
            result = json.loads(
                self.query(
                    '''
                    mutation DepositCreate($user: ID! $amount: Int! $paymentId: String! $category: ID!) {
                        createDeposit(user: $user amount: $amount paymentId: $paymentId category: $category) {
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
                        'category':
                        to_global_id(
                            'DepositCategory',
                            models.DepositCategory.objects.first().id,
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
                        'target': to_global_id('IbisUserNode', target.id),
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
                        'target': to_global_id('IbisUserNode', target.id),
                        'amount': amount,
                        'description': 'This is a transaction',
                    },
                ).content)
            self._client.logout()
            return result

        def withdraw(user, amount):
            if user.balance() - amount >= 0:
                models.Withdrawal.objects.create(
                    user=user,
                    amount=amount,
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
                'donated': x.donated(),
                'fundraised': x.fundraised(),
            }
            for x in models.Organization.objects.all()
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
                else:  # organization donates
                    user = random.choice(list(organization_state.keys()))
                    target = random.choice(list(organization_state.keys()))
                    result = donate(user, target, amount)

                    if organization_state[user]['balance'] - amount >= 0:
                        assert 'errors' not in result
                        organization_state[user]['balance'] -= amount
                        organization_state[user]['donated'] += amount
                        organization_state[target]['balance'] += amount
                        organization_state[target]['fundraised'] += amount
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
                else:  # organization transacts
                    user = random.choice(list(organization_state.keys()))
                    target = random.choice(list(person_state.keys()))
                    result = transact(user, target, amount)

                    if organization_state[user]['balance'] - amount >= 0:
                        assert 'errors' not in result
                        organization_state[user]['balance'] -= amount
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
