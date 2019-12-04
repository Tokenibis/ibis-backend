import graphene
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphql_relay.node.node import from_global_id
from graphene_django.filter import DjangoFilterConnectionField

import notifications.models as models


class NotifierNode(DjangoObjectType):
    class Meta:
        model = models.Notifier
        filter_fields = []
        interfaces = (relay.Node, )


class NotifierUpdate(Mutation):
    class Meta:
        model = models.Notifier

    class Arguments:
        id = graphene.ID(required=True)
        email_follow = graphene.Boolean()
        email_transaction = graphene.Boolean()
        email_comment = graphene.Boolean()
        email_like = graphene.Boolean()
        last_seen = graphene.String()

    notifier = graphene.Field(NotifierNode)

    def mutate(
            self,
            info,
            id,
            email_follow=None,
            email_transaction=None,
            email_comment=None,
            email_like=None,
            last_seen='',
    ):

        notifier = models.Notifier.objects.get(pk=from_global_id(id)[1])
        if type(email_follow) == bool:
            notifier.email_follow = email_follow
        if type(email_transaction) == bool:
            notifier.email_transaction = email_transaction
        if type(email_comment) == bool:
            notifier.email_comment = email_comment
        if type(email_like) == bool:
            notifier.email_like = email_like
        if last_seen:
            notifier.last_seen = last_seen

        notifier.save()
        return NotifierUpdate(notifier=notifier)


class Query(object):
    notifier = relay.Node.Field(NotifierNode)
    all_users = DjangoFilterConnectionField(NotifierNode)


class Mutation(graphene.ObjectType):
    update_notifier = NotifierUpdate.Field()
