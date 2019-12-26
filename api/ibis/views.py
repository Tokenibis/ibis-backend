import os
import sys
import random
import json
import requests

from django.contrib.auth import logout
from django.conf import settings
from rest_framework import generics, response, exceptions, serializers
from users.models import User
from allauth.socialaccount.models import SocialAccount
from graphql_relay.node.node import to_global_id

from .models import IbisUser, Person, Deposit
from .serializers import PaymentSerializer
from .payments import PayPalClient

QUOTE_URL = 'https://api.forismatic.com/api/1.0/?method=getQuote&lang=en&format=jsonp&jsonp=?'
FB_AVATAR = 'https://graph.facebook.com/v4.0/{}/picture?type=large'


class QuoteView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        result = requests.get(QUOTE_URL)
        obj = json.loads(result.text.replace('\\\'', '\'')[2:-1])
        return response.Response({
            'quote':
            obj['quoteText'],
            'author':
            obj['quoteAuthor'] if obj['quoteAuthor'] else 'Unknown',
        })


class PriceView(generics.GenericAPIView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        script_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_path, 'data/prices.json')) as fd:
            self.prices = json.load(fd)

    def get(self, request, *args, **kwargs):
        item = random.choice(list(self.prices.keys()))
        return response.Response({
            'item': item,
            'price': round(self.prices[item] * 100),
        })


class LoginView(generics.GenericAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")
        exists = Person.objects.filter(id=request.user.id).exists()
        if not exists:
            social_accounts = SocialAccount.objects.filter(
                user=request.user.id)
            assert len(social_accounts) == 1, \
                    'New Ibis Users must be authenticated through social accounts'

            social_account = social_accounts[0]
            user = User.objects.get(id=request.user.id)
            person = Person(user_ptr_id=request.user.id)
            person.__dict__.update(user.__dict__)

            if social_account.provider == 'facebook':
                person.avatar = FB_AVATAR.format(social_account.uid)
            else:
                person.avatar = settings.AVATAR_BUCKET.format(
                    hash(str(request.user.id)) % settings.AVATAR_BUCKET_LEN)

            person.score = 0
            person.save()

        return response.Response({
            'user_id':
            to_global_id('PersonNode', str(request.user.id)),
            'is_new_account':
            not exists,
        })


class LogoutView(generics.GenericAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        try:
            logout(request)
            return response.Response({
                'success': True,
            })
        except Exception as e:
            sys.stderr.write('Unexpected exception while logging out')
            sys.stderr.write(e)


class IdentifyView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        if Person.objects.filter(id=request.user.id).exists():
            user_id = to_global_id('PersonNode', str(request.user.id))
        else:
            user_id = ''

        return response.Response({'user_id': user_id})


class PaymentView(generics.GenericAPIView):
    serializer_class = PaymentSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paypal_client = PayPalClient()

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")
        payment_id, amount = self.paypal_client.get_order(
            request.data['orderID'])

        if not (payment_id and amount):
            print('Error fetching order information')
            return {
                'depositID': '',
            }

        user = IbisUser.objects.get(pk=request.user.id)
        deposit = Deposit.objects.create(
            user=user,
            amount=amount,
            payment_id='paypal:{}'.format(payment_id),
        )
        deposit.save()

        return response.Response({
            'depositID':
            to_global_id('DepositNode', deposit.id),
        })
