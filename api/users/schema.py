import graphene

from graphene import relay
from graphql import GraphQLError
from graphql_relay.node.node import from_global_id
from graphene_django import DjangoObjectType
from allauth.socialaccount.models import SocialAccount

import users.models as models


class UserNode(DjangoObjectType):
    social_ID = graphene.String()
    email = graphene.String(required=True)

    class Meta:
        model = models.User
        exclude = ['password']
        filter_fields = ['id', 'username']
        interfaces = (relay.Node, )

    def resolve_social_ID(self, *args, **kwargs):
        try:
            return SocialAccount.objects.get(user=self).uid
        except SocialAccount.DoesNotExist:
            return ''

    def resolve_email(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.id):
            raise GraphQLError('You do not have sufficient permission')

        return self.email


class Query(object):
    user = relay.Node.Field(UserNode)
