import os
import sys
import random
import json
import requests
import ftfy
import logging

from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from rest_framework import generics, response, exceptions, serializers
from users.models import GeneralUser
from allauth.socialaccount.models import SocialAccount
from graphql_relay.node.node import to_global_id
from django.utils.timezone import localtime, now

import ibis.models as models
from .serializers import PasswordLoginSerializer, PasswordChangeSerializer
from .serializers import PaymentSerializer
from .payments import PayPalClient

logger = logging.getLogger(__name__)

QUOTE_URL = 'https://api.forismatic.com/api/1.0/?method=getQuote&lang=en&format=jsonp&jsonp=?'
FB_AVATAR = 'https://graph.facebook.com/v4.0/{}/picture?type=large'
ANONYMOUS_AVATAR = 'https://s3.us-east-2.amazonaws.com/app.tokenibis.org/miscellaneous/confused_robot.jpg'


class QuoteView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        result = requests.get(QUOTE_URL)
        obj = json.loads(result.text.replace('\\\'', '\'')[2:-1])
        return response.Response({
            'quote':
            ftfy.fix_text(obj['quoteText']),
            'author':
            ftfy.fix_text(obj['quoteAuthor'])
            if obj['quoteAuthor'] else 'Unknown',
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

        if not models.Person.objects.filter(id=request.user.id).exists():
            social_accounts = SocialAccount.objects.filter(
                user=request.user.id)
            if len(social_accounts) != 1:
                raise exceptions.AuthenticationFailed(
                    detail=
                    'New Ibis Users must be authenticated through social accounts'
                )

            social_account = social_accounts[0]
            user = GeneralUser.objects.get(id=request.user.id)

            # return error message
            if social_account.provider == 'microsoft' and user.email.rsplit(
                    '@')[-1] != 'unm.edu':
                raise exceptions.AuthenticationFailed(
                    detail='Please use a valid unm.edu email address')

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
            to_global_id('UserNode', str(request.user.id)),
            'user_type':
            'person',
        })


class PasswordLoginView(generics.GenericAPIView):
    serializer_class = PasswordLoginSerializer

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail='No valid values')

        user = authenticate(
            username=request.data['username'],
            password=request.data['password'],
        )

        if user is not None:
            login(request, user)
            return response.Response({
                'user_id':
                to_global_id('UserNode', str(user.id)),
                'user_type':
                'person' if models.Person.objects.filter(
                    id=user.id) else 'organization',
            })
        else:
            return response.Response({
                'user_id': '',
                'user_type': '',
            })


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail='No valid values')

        if not request.user.check_password(
                serializerform.data['password_old']):
            return response.Response({
                'success': False,
                'message': 'current password is wrong',
            })

        try:
            validate_password(serializerform.data['password_new'])
        except ValidationError as e:
            return response.Response({
                'success': False,
                'message': e.messages[0],
            })

        # set_password also hashes the password that the user will get
        request.user.set_password(serializerform.data['password_new'])
        request.user.save()
        update_session_auth_hash(request, request.user)

        return response.Response({
            'success': True,
            'message': 'Password successfully updated',
        })


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

        person.date_joined = localtime(now()).replace(
            year=2019,
            month=4,
            day=5,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        person.save()

        return response.Response({
            'user_id':
            to_global_id('UserNode', str(person.user_ptr.id)),
            'user_type':
            'person',
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
        if models.User.objects.filter(id=request.user.id).exists():
            user_id = to_global_id('UserNode', str(request.user.id))
            user_type = 'person' if models.Person.objects.filter(
                id=request.user.id).exists() else 'organization'
        else:
            user_id = ''
            user_type = ''

        return response.Response({'user_id': user_id, 'user_type': user_type})


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
            logger.error('Error fetching order information')
            return response.Response({
                'depositID': '',
            })

        user = models.User.objects.get(pk=request.user.id)
        deposit = models.Deposit.objects.create(
            user=user,
            amount=net,
            payment_id='paypal:{}:{}'.format(fee, payment_id),
            category=models.DepositCategory.objects.get(title='paypal'),
        )

        return response.Response({
            'depositID':
            to_global_id('DepositNode', deposit.id),
        })
