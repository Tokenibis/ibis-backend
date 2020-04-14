import django_filters
import graphene
from graphql import GraphQLError
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphql_relay.node.node import from_global_id
from graphene_django.filter import DjangoFilterConnectionField

import notifications.models as models
import ibis.models

# --- Notifier -------------------------------------------------------------- #


class NotifierNode(DjangoObjectType):

    email_follow = graphene.Boolean()
    email_transaction = graphene.Boolean()
    email_donation = graphene.Boolean()
    email_comment = graphene.Boolean()
    email_ubp = graphene.Boolean()
    email_deposit = graphene.Boolean()
    email_like = graphene.Boolean()
    email_feed = graphene.String()

    last_seen = graphene.String()
    unseen_count = graphene.Int()

    class Meta:
        model = models.Notifier
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_email_following(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_following

    def resolve_email_transaction(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_transaction

    def resolve_email_donation(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_transaction

    def resolve_email_comment(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_comment

    def resolve_email_ubp(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_ubp

    def resolve_email_deposit(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_deposit

    def resolve_email_like(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_like

    def resolve_email_feed(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_feed

    def resolve_last_seen(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.last_seen

    def resolve_unseen_count(self, info, *args, **kwargs):
        if not (info.context.user.is_staff
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.unseen_count()

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_staff:
            return queryset
        return queryset.filter(user=info.context.user)


class NotifierUpdate(Mutation):
    class Meta:
        model = models.Notifier

    class Arguments:
        id = graphene.ID(required=True)
        email_follow = graphene.Boolean()
        email_transaction = graphene.Boolean()
        email_comment = graphene.Boolean()
        email_like = graphene.Boolean()
        email_news = graphene.Boolean()
        email_event = graphene.Boolean()
        email_post = graphene.Boolean()
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
            email_news=None,
            email_event=None,
            email_post=None,
            last_seen='',
    ):

        notifier = models.Notifier.objects.get(pk=from_global_id(id)[1])

        if not (info.context.user.is_staff
                or info.context.user.id == notifier.user.id):
            raise GraphQLError('You do not have sufficient permission')

        if type(email_follow) == bool:
            notifier.email_follow = email_follow
        if type(email_transaction) == bool:
            notifier.email_transaction = email_transaction
        if type(email_comment) == bool:
            notifier.email_comment = email_comment
        if type(email_like) == bool:
            notifier.email_like = email_like
        if type(email_news) == bool:
            notifier.email_news = email_news
        if type(email_event) == bool:
            notifier.email_event = email_event
        if type(email_post) == bool:
            notifier.email_post = email_post
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
        notifier = ibis.models.IbisUser.objects.get(
            pk=from_global_id(value)[1]).notifier
        return qs.filter(notifier=notifier)


class NotificationNode(DjangoObjectType):
    class Meta:
        model = models.Notification

        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_staff:
            return queryset
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')

        return queryset.filter(notifier__user=info.context.user)


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

        if type(clicked) == bool:
            if not (info.context.user.is_staff
                    or info.context.user.id == notification.notifier.user.id):
                raise GraphQLError('You do not have sufficient permission')
            notification.clicked = clicked

        if notifier:
            if not info.context.user.is_staff:
                raise GraphQLError('You are not a staff member')
            notification.notifier = models.Notifier.objects.get(
                pk=from_global_id(notifier)[1])

        if category:
            if not info.context.user.is_staff:
                raise GraphQLError('You are not a staff member')
            assert category in [
                x[0] for x in models.Notification.NOTIFICATION_CATEGORY
            ]
            notification.category = category

        if reference:
            if not info.context.user.is_staff:
                raise GraphQLError('You are not a staff member')
            notification.reference = reference

        if description:
            if not info.context.user.is_staff:
                raise GraphQLError('You are not a staff member')
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
