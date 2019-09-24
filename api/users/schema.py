import graphene

from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from allauth.socialaccount.models import SocialAccount

import users.models as models


class UserNode(DjangoObjectType):
    facebook_ID = graphene.String()

    class Meta:
        model = models.User
        filter_fields = ['id', 'username']
        interfaces = (relay.Node, )

    def resolve_facebook_ID(self, *args, **kwargs):
        try:
            return SocialAccount.objects.get(user=self).uid
        except SocialAccount.DoesNotExist:
            return ''


class Query(object):
    user = relay.Node.Field(UserNode)
    all_users = DjangoFilterConnectionField(UserNode)
