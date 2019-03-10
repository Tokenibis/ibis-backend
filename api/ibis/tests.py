from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.views import status
from .models import Transaction
from users.models import User
from users.serializers import UsersSerializer


class BaseViewTest(APITestCase):
    client = APIClient()

    @staticmethod
    def create_user(nickname=''):
        if nickname:
            User.objects.create(username=nickname, nickname=nickname)

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
        self.create_user('Alice')
        self.create_user('Bob')


class GetAllTransactionsTest(BaseViewTest):
    def test_get_all_transactions(self):

        # hit the API endpoint
        response = self.client.get(
            reverse('users-all', kwargs={'version': 'v1'}))
        # fetch the data from db
        expected = User.objects.all()
        serialized = UsersSerializer(expected, many=True)

        self.assertEqual(response.data, serialized.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
