import os
import sys
import json
import ftfy
import boto3
import random
import logging
import requests
import ibis.serializers
import ibis.models as models

from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import login, logout, authenticate
from django.conf import settings
from rest_framework import generics, response, exceptions, serializers
from users.models import GeneralUser
from allauth.socialaccount.models import SocialAccount
from graphql_relay.node.node import to_global_id
from django.utils.timezone import localtime, timedelta

from api.utils import get_submodel

logger = logging.getLogger(__name__)


class QuoteView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        result = requests.get(settings.QUOTE_URL)
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

            person = models.Person(user_ptr_id=request.user.id)
            person.__dict__.update(user.__dict__)

            person.username = models.generate_valid_username(
                person.first_name,
                person.last_name,
            )

            if social_account.provider == 'facebook':
                person.avatar = settings.FACEBOOK_AVATAR.format(
                    social_account.uid)
            else:
                person.avatar = settings.AVATAR_BUCKET.format(
                    hash(str(request.user.id)) % settings.AVATAR_BUCKET_LEN)

            if 'referral' in request.data:
                person.referral = request.data['referral']

            person.save()

        return response.Response({
            'user_id':
            to_global_id('UserNode', str(request.user.id)),
            'user_type':
            get_submodel(models.User.objects.get(id=request.user.id)).__name__,
        })


class PasswordLoginView(generics.GenericAPIView):
    serializer_class = ibis.serializers.PasswordLoginSerializer

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
                get_submodel(models.User.objects.get(id=user.id)).__name__,
            })
        else:
            return response.Response({
                'user_id': '',
                'user_type': '',
            })


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = ibis.serializers.PasswordChangeSerializer

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
            user_type = get_submodel(
                models.User.objects.get(id=request.user.id)).__name__
        else:
            user_id = ''
            user_type = ''

        return response.Response({'user_id': user_id, 'user_type': user_type})


class PhoneNumberView(generics.GenericAPIView):
    serializer_class = ibis.serializers.PhoneNumberSerializer

    client = boto3.client(
        'sns',
        region_name=settings.AWS_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    message = 'Token Ibis Verification Code: {}'

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")

        code = str(random.randint(100000, 999999))

        request.session['ibis_phone_number'] = request.data['number']
        request.session['ibis_phone_code'] = code
        request.session['ibis_phone_timestamp'] = localtime().timestamp()

        self.client.publish(
            PhoneNumber=request.data['number'],
            Message=self.message.format(code),
        )

        return response.Response({
            'success': True,
        })


class PhoneCodeView(generics.GenericAPIView):
    serializer_class = ibis.serializers.PhoneCodeSerializer

    def post(self, request, *args, **kwargs):
        assert request.session.get('ibis_phone_number')
        assert request.session.get('ibis_phone_code')
        assert request.session.get('ibis_phone_timestamp')

        user = models.Person.objects.get(id=request.user.id)

        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail='No valid values')

        matches = request.session['ibis_phone_code'] == request.data[
            'code'] and localtime().timestamp(
            ) < request.session['ibis_phone_timestamp'] + timedelta(
                hours=1).total_seconds()

        other_users = list(
            models.Person.objects.exclude(id=request.user.id).filter(
                phone_number=request.session['ibis_phone_number'],
                verified=True,
            ))

        user.phone_number = request.session['ibis_phone_number']

        if matches and not other_users:
            user.verified = True
            user.verified_original = True

        user.save()

        request.session['ibis_phone_matches'] = matches

        return response.Response({
            'matches':
            matches,
            'verified':
            user.verified,
            'other_users': [[
                to_global_id('UserNode', x.id),
                x.username,
            ] for x in other_users],
        })


class PhoneConfirmView(generics.GenericAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        assert request.session.get('ibis_phone_number')
        assert request.session.get('ibis_phone_matches')

        user = models.Person.objects.get(id=request.user.id)

        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")

        for other_user in list(
                models.Person.objects.filter(
                    phone_number=request.session['ibis_phone_number'])):
            other_user.verified = False
            other_user.verified_original = False
            other_user.save()

        user.verified = True
        user.save()

        return response.Response({
            'success': True,
        })
