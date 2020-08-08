import django_filters
import graphene

from django.db.models import Value, PositiveIntegerField
from graphql import GraphQLError
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphql_relay.node.node import from_global_id
from graphene_django.filter import DjangoFilterConnectionField, GlobalIDFilter

import notifications.models as models
import ibis.models

# --- Notifier -------------------------------------------------------------- #


class NotifierNode(DjangoObjectType):
    email_follow = graphene.Boolean()
    email_donation = graphene.Boolean()
    email_transaction = graphene.Boolean()
    email_comment = graphene.Boolean()
    email_mention = graphene.Boolean()
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
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_following

    def resolve_email_donation(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_donation

    def resolve_email_transaction(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_transaction

    def resolve_email_comment(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_comment

    def resolve_email_mention(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_mention

    def resolve_email_ubp(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_ubp

    def resolve_email_deposit(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_deposit

    def resolve_email_like(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_like

    def resolve_email_feed(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.email_feed

    def resolve_last_seen(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.last_seen

    def resolve_unseen_count(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.user.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.unseen_count()

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset
        return queryset.filter(user=info.context.user)


class NotifierUpdate(Mutation):
    class Meta:
        model = models.Notifier

    class Arguments:
        id = graphene.ID(required=True)
        email_follow = graphene.Boolean()
        email_transaction = graphene.Boolean()
        email_donation = graphene.Boolean()
        email_deposit = graphene.Boolean()
        email_ubp = graphene.Boolean()
        email_comment = graphene.Boolean()
        email_mention = graphene.Boolean()
        email_like = graphene.Boolean()
        email_feed = graphene.String()
        last_seen = graphene.String()

    notifier = graphene.Field(NotifierNode)

    def mutate(
            self,
            info,
            id,
            email_follow=None,
            email_transaction=None,
            email_donation=None,
            email_deposit=None,
            email_ubp=None,
            email_comment=None,
            email_mention=None,
            email_like=None,
            email_feed=None,
            last_seen='',
    ):

        notifier = models.Notifier.objects.get(pk=from_global_id(id)[1])

        if not (info.context.user.is_superuser
                or info.context.user.id == notifier.user.id):
            raise GraphQLError('You do not have sufficient permission')

        if type(email_follow) == bool:
            notifier.email_follow = email_follow
        if type(email_transaction) == bool:
            notifier.email_transaction = email_transaction
        if type(email_donation) == bool:
            notifier.email_donation = email_donation
        if type(email_deposit) == bool:
            notifier.email_deposit = email_deposit
        if type(email_ubp) == bool:
            notifier.email_ubp = email_ubp
        if type(email_comment) == bool:
            notifier.email_comment = email_comment
        if type(email_mention) == bool:
            notifier.email_mention = email_mention
        if type(email_like) == bool:
            notifier.email_like = email_like
        if email_feed:
            notifier.email_feed = email_feed
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
    category = graphene.String()

    class Meta:
        model = models.Notification

        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')

        return queryset.filter(notifier__user=info.context.user)

    def resolve_category(self, *args, **kwargs):
        return models.get_submodel(
            self,
            models.Notification,
        ).__name__.replace('Notification', '').lower()


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
            if not (info.context.user.is_superuser
                    or info.context.user.id == notification.notifier.user.id):
                raise GraphQLError('You do not have sufficient permission')
            notification.clicked = clicked

        if notifier:
            if not info.context.user.is_superuser:
                raise GraphQLError('You are not a staff member')
            notification.notifier = models.Notifier.objects.get(
                pk=from_global_id(notifier)[1])

        if category:
            if not info.context.user.is_superuser:
                raise GraphQLError('You are not a staff member')
            assert category in [
                x[0] for x in models.Notification.NOTIFICATION_CATEGORY
            ]
            notification.category = category

        if reference:
            if not info.context.user.is_superuser:
                raise GraphQLError('You are not a staff member')
            notification.reference = reference

        if description:
            if not info.context.user.is_superuser:
                raise GraphQLError('You are not a staff member')
            notification.description = description

        notification.save()
        return NotificationUpdate(notification=notification)


class DonationMessageFilter(django_filters.FilterSet):
    organization = GlobalIDFilter(method='filter_organization')
    random = django_filters.BooleanFilter(method='filter_random')

    class Meta:
        model = models.DonationMessage
        fields = []

    def filter_random(self, qs, name, value):
        return qs.order_by('?')

    def filter_organization(self, qs, name, value):
        return qs.annotate(
            organization_id=Value(
                from_global_id(value)[1],
                output_field=PositiveIntegerField(),
            ))


class DonationMessageNode(DjangoObjectType):
    description = graphene.String()

    class Meta:
        model = models.DonationMessage
        filter_fields = []
        interfaces = (relay.Node, )

    class Arguments:
        test = graphene.String()

    def resolve_description(self, *args, **kwargs):
        if hasattr(self, 'organization_id'):
            return self.description.format(
                organization=ibis.models.Organization.objects.get(
                    id=self.organization_id))
        return self.description


# --------------------------------------------------------------------------- #


class Query(object):
    notifier = relay.Node.Field(NotifierNode)
    notification = relay.Node.Field(NotificationNode)

    all_notifiers = DjangoFilterConnectionField(NotifierNode)
    all_notifications = DjangoFilterConnectionField(
        NotificationNode,
        filterset_class=NotificationFilter,
    )
    all_donation_messages = DjangoFilterConnectionField(
        DonationMessageNode,
        filterset_class=DonationMessageFilter,
    )


class Mutation(graphene.ObjectType):
    update_notifier = NotifierUpdate.Field()
    update_notification = NotificationUpdate.Field()
