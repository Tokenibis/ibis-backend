from rest_framework import generics, response, exceptions, serializers
from .models import IbisUser, Person
from users.models import User
from allauth.socialaccount.models import SocialAccount
from graphql_relay.node.node import to_global_id

FB_AVATAR = 'https://graph.facebook.com/v4.0/{}/picture?type=large'


class LoginView(generics.GenericAPIView):
    serializer_class = serializers.Serializer

    def post(self, request, *args, **kwargs):
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")
        # attempt to create a new ibis user if one doesn't exist
        # return the graph id
        exists = IbisUser.objects.filter(id=request.user.id).exists()
        if not exists:
            social_accounts = SocialAccount.objects.filter(
                user=request.user.id)
            assert len(social_accounts) == 1, \
                    'New Ibis Users must be authenticated through social accounts'

            social_account = social_accounts[0]
            assert social_account.provider == 'facebook', \
                    'Only Facebook authentication is supported at this time'

            user = User.objects.get(id=request.user.id)
            person = Person(user_ptr_id=request.user.id)
            person.__dict__.update(user.__dict__)
            person.avatar = FB_AVATAR.format(social_account.uid)
            person.score = 0
            person.save()

        return response.Response({
            'user_id':
            to_global_id('PersonNode', str(request.user.id)),
            'is_new_account':
            not exists,
        })


class IdentifyView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        return response.Response({
            'user_id':
            to_global_id('PersonNode', str(request.user.id)) if request.user.id else '',
        })
