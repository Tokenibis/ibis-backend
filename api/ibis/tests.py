from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.views import status
from .models import Transaction
from profiles.models import Profile
from profiles.serializers import ProfilesSerializer


class BaseViewTest(APITestCase):
    client = APIClient()

    @staticmethod
    def create_profile(nickname=''):
        if nickname:
            Profile.objects.create(nickname=nickname)

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
        self.create_profile('Alice')
        self.create_profile('Bob')


class GetAllTransactionsTest(BaseViewTest):
    def test_get_all_transactions(self):

        # hit the API endpoint
        response = self.client.get(
            reverse('profiles-all', kwargs={'version': 'v1'}))
        # fetch the data from db
        expected = Profile.objects.all()
        serialized = ProfilesSerializer(expected, many=True)

        self.assertEqual(response.data, serialized.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
