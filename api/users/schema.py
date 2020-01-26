import graphene

from graphene import relay
from graphene_django import DjangoObjectType
from allauth.socialaccount.models import SocialAccount

import users.models as models


class UserNode(DjangoObjectType):
    social_ID = graphene.String()

    class Meta:
        model = models.User
        filter_fields = ['id', 'username']
        interfaces = (relay.Node, )

    def resolve_social_ID(self, *args, **kwargs):
        try:
            return SocialAccount.objects.get(user=self).uid
        except SocialAccount.DoesNotExist:
            return ''


class Query(object):
    user = relay.Node.Field(UserNode)
