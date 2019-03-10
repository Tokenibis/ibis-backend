from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

import users.models as models


class UserNode(DjangoObjectType):
    class Meta:
        model = models.User
        filter_fields = ['id', 'username']
        interfaces = (relay.Node, )


class Query(object):
    user = relay.Node.Field(UserNode)
    all_users = DjangoFilterConnectionField(UserNode)
