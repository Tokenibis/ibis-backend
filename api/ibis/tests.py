from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.views import status
from .models import Account, Transaction
from .serializers import AccountsSerializer


class BaseViewTest(APITestCase):
    client = APIClient()

    @staticmethod
    def create_account(nickname=''):
        if nickname:
            Account.objects.create(nickname='Alice')

    @staticmethod
    def create_transaction(sender='', receiver='', amount=0, description=''):
        if sender and receiver and amount and description:
            Transaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount,
                description=description)

    def setUp(self):
        # add test data
        self.create_account('Alice')
        self.create_account('Bob')


class GetAllTransactionsTest(BaseViewTest):
    def test_get_all_transactions(self):

        # hit the API endpoint
        response = self.client.get(
            reverse('accounts-all', kwargs={'version': 'v1'}))
        # fetch the data from db
        expected = Account.objects.all()
        serialized = AccountsSerializer(expected, many=True)

        self.assertEqual(response.data, serialized.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
