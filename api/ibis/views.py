import os
import sys
import random
import json
import requests

from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from rest_framework import generics, response, exceptions, serializers
from users.models import User
from allauth.socialaccount.models import SocialAccount
from graphql_relay.node.node import to_global_id
from django.utils.timezone import localtime, now

import ibis.models as models
from .serializers import PasswordLoginSerializer, PaymentSerializer
from .payments import PayPalClient

QUOTE_URL = 'https://api.forismatic.com/api/1.0/?method=getQuote&lang=en&format=jsonp&jsonp=?'
FB_AVATAR = 'https://graph.facebook.com/v4.0/{}/picture?type=large'
ANONYMOUS_AVATAR = 'https://s3.us-east-2.amazonaws.com/app.tokenibis.org/miscellaneous/confused_robot.jpg'


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
        exists = models.Person.objects.filter(id=request.user.id).exists()
        if not exists:
            social_accounts = SocialAccount.objects.filter(
                user=request.user.id)
            assert len(social_accounts) == 1, \
                'New Ibis Users must be authenticated through social accounts'

            social_account = social_accounts[0]
            user = User.objects.get(id=request.user.id)
            person = models.Person(user_ptr_id=request.user.id)
            person.__dict__.update(user.__dict__)

            person.username = models.generate_valid_username(
                person.first_name,
                person.last_name,
            )

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


class PasswordLoginView(generics.GenericAPIView):
    serializer_class = PasswordLoginSerializer

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")

        user = authenticate(
            username=request.data['username'],
            password=request.data['password'],
        )
        if user is not None:
            login(request, user)
            return response.Response({'success': True})
        else:
            return response.Response({'success': False})


class AnonymousLoginView(generics.GenericAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        exists = models.Person.objects.filter(username='anonymous').exists()
        if not exists:
            person = models.Person.objects.create(
                username='anonymous',
                email='anonymous@example.com',
                first_name='Anonymous',
                last_name='Robot',
                avatar=ANONYMOUS_AVATAR,
            )

        else:
            person = models.Person.objects.get(username='anonymous')

        login(request, person.user_ptr)

        person.date_joined = localtime(now().replace(
            year=2019,
            month=4,
            day=5,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ))
        person.save()

        return response.Response({
            'user_id':
            to_global_id('PersonNode', str(person.user_ptr.id)),
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
        if models.Person.objects.filter(id=request.user.id).exists():
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
        payment_id, net, fee = self.paypal_client.get_order(
            request.data['orderID'])

        if not (payment_id and net):
            print('Error fetching order information')
            return response.Response({
                'depositID': '',
            })

        user = models.IbisUser.objects.get(pk=request.user.id)
        deposit = models.Deposit.objects.create(
            user=user,
            amount=net,
            payment_id='paypal:{}:{}'.format(fee, payment_id),
        )

        return response.Response({
            'depositID':
            to_global_id('DepositNode', deposit.id),
        })
