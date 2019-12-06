import django_filters
import graphene
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphql_relay.node.node import from_global_id
from graphene_django.filter import DjangoFilterConnectionField

import notifications.models as models

# --- Notifier -------------------------------------------------------------- #


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


# --- Notifications --------------------------------------------------------- #


class NotificationFilter(django_filters.FilterSet):
    for_user = django_filters.CharFilter(method='filter_for_user')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.Notification
        fields = []

    def filter_for_user(self, qs, name, value):
        notifier = models.Person(pk=from_global_id(value)[1]).notifier
        return qs.filter(notifier=notifier)


class NotificationNode(DjangoObjectType):
    class Meta:
        model = models.Notification

        filter_fields = []
        interfaces = (relay.Node, )


class NotificationUpdate(Mutation):
    class Meta:
        model = models.Notification

    class Arguments:
        id = graphene.ID(required=True)
        notifier = graphene.ID()
        category = graphene.String()
        clicked = graphene.Boolean()
        reference = graphene.String()
        description = graphene.String()

    notification = graphene.Field(NotificationNode)

    def mutate(
            self,
            info,
            id,
            notifier=None,
            category='',
            clicked=None,
            reference='',
            description='',
    ):

        notification = models.Notification.objects.get(
            pk=from_global_id(id)[1])
        if notifier:
            notification.notifier = models.Notifier.objects.get(
                pk=from_global_id(notifier)[1])
        if category:
            assert category in [
                x[0] for x in models.Notification.NOTIFICATION_CATEGORY
            ]
            notification.category = category
        if type(clicked) == bool:
            notification.clicked = clicked
        if reference:
            notification.reference = reference
        if description:
            notification.description = description

        notification.save()
        return NotificationUpdate(notification=notification)


# --------------------------------------------------------------------------- #


class Query(object):
    notifier = relay.Node.Field(NotifierNode)
    notification = relay.Node.Field(NotificationNode)

    all_notifiers = DjangoFilterConnectionField(NotifierNode)
    all_notifications = DjangoFilterConnectionField(
        NotificationNode,
        filterset_class=NotificationFilter,
    )


class Mutation(graphene.ObjectType):
    update_notifier = NotifierUpdate.Field()
    update_notification = NotificationUpdate.Field()
