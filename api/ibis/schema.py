import os
import django_filters
import graphene
import dateutil.parser
import ibis.models as models

from django.core.exceptions import FieldError
from django.db.models import Q, Count, Value, Subquery, OuterRef
from django.db.models.functions import Concat
from django.conf import settings
from django.utils.timezone import localtime
from graphql import GraphQLError
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id, to_global_id
from graphene_file_upload.scalars import Upload
from users.schema import GeneralUserNode
from api.utils import get_submodel

AVATAR_SIZE = (528, 528)


class UserNodeInterface(relay.Node):
    @staticmethod
    def to_global_id(type, id):
        return to_global_id(UserNode.__name__, id)

    @staticmethod
    def get_node_from_global_id(info, global_id, only_type=None):
        if only_type:
            return only_type.get_node(info, from_global_id(global_id)[1])
        return UserNode.get_node(info, from_global_id(global_id)[1])


class EntryNodeInterface(relay.Node):
    @staticmethod
    def to_global_id(type, id):
        return to_global_id(EntryNode.__name__, id)

    @staticmethod
    def get_node_from_global_id(info, global_id, only_type=None):
        if only_type:
            return only_type.get_node(info, from_global_id(global_id)[1])
        return EntryNode.get_node(info, from_global_id(global_id)[1])


# --- Filters --------------------------------------------------------------- #


class UserOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super(UserOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['follower_count', '-follower_count']:
                if v in value:
                    qs = qs.annotate(
                        follower_count=Count('follower')).order_by(v)
                    value.remove(v)
            for v in ['messaged_last', '-messaged_last']:
                if v in value:
                    try:
                        qs = qs.order_by(v)
                    except FieldError:
                        raise GraphQLError(
                            'You do not have sufficient permission')
                        value.remove(v)

        return super(UserOrderingFilter, self).filter(qs, value)


class UserFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(method='filter_id')
    followed_by = django_filters.CharFilter(method='filter_followed_by')
    follower_of = django_filters.CharFilter(method='filter_follower_of')
    like_for = django_filters.CharFilter(method='filter_like_for')
    rsvp_for = django_filters.CharFilter(method='filter_rsvp_for')
    mention_in = django_filters.CharFilter(method='filter_mention_in')
    messaged_with = django_filters.CharFilter(method='filter_messaged_with')
    order_by = UserOrderingFilter(
        fields=(
            ('score', 'score'),
            ('date_joined', 'date_joined'),
            ('follower_count', 'follower_count'),
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
            ('messaged_last', 'messaged_last'),
        ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.User
        fields = []

    def filter_id(self, qs, name, value):
        return qs.filter(id=from_global_id(value)[1])

    def filter_followed_by(self, qs, name, value):
        return qs.filter(
            id__in=self.Meta.model.objects.get(
                id=from_global_id(value)[1]).following.all())

    def filter_follower_of(self, qs, name, value):
        return qs.filter(
            id__in=self.Meta.model.objects.get(
                id=from_global_id(value)[1]).follower.all())

    def filter_like_for(self, qs, name, value):
        entry_obj = models.Entry.objects.get(pk=from_global_id(value)[1])
        entry_sub_obj = get_submodel(entry_obj).objects.get(
            pk=from_global_id(value)[1])
        if self.request.user.is_superuser or any(
                x.objects.filter(pk=from_global_id(value)[1]).exists()
                for x in [
                    models.News,
                    models.Event,
                    models.Post,
                    models.Activity,
                ]) or entry_sub_obj.user.id == self.request.user.id:
            return qs.filter(id__in=entry_obj.like.all())
        else:
            return qs.filter(id__in=entry_obj.like.all()).filter(
                id=self.request.user.id)

    def filter_rsvp_for(self, qs, name, value):
        return qs.filter(
            id__in=get_submodel(
                models.Entry.objects.get(
                    pk=from_global_id(value)[1])).objects.get(
                        id=from_global_id(value)[1]).rsvp.all())

    def filter_mention_in(self, qs, name, value):
        entry_obj = models.Entry.objects.get(pk=from_global_id(value)[1])
        return qs.filter(id__in=entry_obj.mention.all())

    def filter_messaged_with(self, qs, name, value):
        user_obj = models.User.objects.get(pk=from_global_id(value)[1])
        return qs.filter(
            Q(id__in=user_obj.messagedirect_set.values('target'))
            | Q(id__in=user_obj.message_received.values('user'))).annotate(
                messaged_last=Subquery(
                    models.MessageDirect.objects.filter(
                        Q(user=OuterRef('id'), target=user_obj)
                        | Q(user=user_obj, target=OuterRef('id'))).order_by(
                            '-created').values('created')[:1])).order_by(
                                '-messaged_last')

    def filter_search(self, qs, name, value):
        return qs.annotate(
            name=Concat('first_name', Value(' '), 'last_name')).filter(
                Q(name__icontains=value) | Q(username__icontains=value))


class PersonFilter(UserFilter):
    verified = django_filters.BooleanFilter(method='filter_verified')
    verified_original = django_filters.BooleanFilter(
        method='filter_verified_original')

    class Meta:
        model = models.Person
        fields = []

    def filter_verified(self, qs, name, value):
        return qs.filter(verified=value)

    def filter_verified_original(self, qs, name, value):
        return qs.filter(verified_original=value)


class DepositFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(method='filter_user')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))

    def filter_user(self, qs, name, value):
        return qs.filter(Q(user_id=from_global_id(value)[1]))


class WithdrawalFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(method='filter_user')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))

    def filter_user(self, qs, name, value):
        return qs.filter(Q(user_id=from_global_id(value)[1]))


class InvestmentFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(method='filter_user')
    order_by = django_filters.OrderingFilter(fields=(('start', 'start'), ))

    def filter_user(self, qs, name, value):
        return qs.filter(Q(user_id=from_global_id(value)[1]))


class InvestmentDonationFilter(django_filters.FilterSet):
    with_donation = django_filters.CharFilter(
        method='filter_with_donation')

    with_investment = django_filters.CharFilter(
        method='filter_with_investment')

    class Meta:
        model = models.InvestmentDonation
        fields = []

    def filter_with_donation(self, qs, name, value):
        return qs.filter(donation=from_global_id(value)[1])

    def filter_with_investment(self, qs, name, value):
        return qs.filter(investment=from_global_id(value)[1])


class EntryOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['like_count', '-like_count']:
                if v in value:
                    qs = qs.annotate(like_count=Count('like')).order_by(v)
                    value.remove(v)

        return super().filter(qs, value)


class EntryFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(method='filter_user')
    scratch = django_filters.CharFilter(method='filter_scratch')
    by_following = django_filters.CharFilter(method='filter_by_following')
    bookmark_by = django_filters.CharFilter(method='filter_bookmark_by')
    created_after = django_filters.CharFilter(method='filter_created_after')
    created_before = django_filters.CharFilter(method='filter_created_before')
    search = django_filters.CharFilter(method='filter_search')

    order_by = EntryOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))

    class Meta:
        model = models.Entry
        fields = []

    def filter_user(self, qs, name, value):
        return qs.filter(user_id=from_global_id(value)[1])

    def filter_scratch(self, qs, name, value):
        if not (self.request.user.is_superuser
                or self.request.user.id == int(from_global_id(value)[1])):
            raise GraphQLError('You do not have sufficient permission')
        return qs.filter(scratch=value)

    def filter_by_following(self, qs, name, value):
        return qs.filter(
            user_id__in=models.User.objects.get(
                id=int(from_global_id(value)[1])).following.all())

    def filter_bookmark_by(self, qs, name, value):
        if not (self.request.user.is_superuser
                or self.request.user.id == int(from_global_id(value)[1])):
            raise GraphQLError('You do not have sufficient permission')

        return qs.filter(
            id__in=models.User.objects.get(
                id=from_global_id(value)[1]).bookmark_for.all())

    def filter_created_after(self, qs, name, value):
        return qs.filter(created__gte=value)

    def filter_created_before(self, qs, name, value):
        return qs.filter(created__lt=value)

    def filter_search(self, qs, name, value):
        return qs.filter(description__icontains=value)


class TransferFilter(EntryFilter):
    with_user = django_filters.CharFilter(method='filter_with_user')
    with_following = django_filters.CharFilter(method='filter_with_following')

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat(
                'user__first_name',
                Value(' '),
                'user__last_name',
            ), ).annotate(
                target_name=Concat(
                    'target__first_name',
                    Value(' '),
                    'target__last_name',
                ), ).filter(
                    Q(user_name__icontains=value)
                    | Q(target_name__icontains=value)
                    | Q(user__username__icontains=value)
                    | Q(target__username__icontains=value)
                    | Q(description__icontains=value))

    def filter_with_user(self, qs, name, value):
        return qs.filter(
            Q(user_id=from_global_id(value)[1])
            | Q(target_id=from_global_id(value)[1]))

    def filter_with_following(self, qs, name, value):
        return qs.filter(
            Q(
                target_id__in=models.User.objects.get(
                    id=int(from_global_id(value)[1])).following.all()) | Q(
                        user_id__in=models.User.objects.get(
                            id=int(from_global_id(value)[1])).following.all()))


class DonationFilter(TransferFilter):
    with_investment = django_filters.CharFilter(
        method='filter_with_investment')

    class Meta:
        model = models.Donation
        fields = []

    def filter_with_investment(self, qs, name, value):
        return qs.filter(funded_by=from_global_id(value)[1])


class RewardFilter(TransferFilter):
    related_activity = django_filters.CharFilter(
        method='filter_related_activity')

    class Meta:
        model = models.Reward
        fields = []

    def filter_related_activity(self, qs, name, value):
        return qs.filter(related_activity=from_global_id(value)[1])


class NewsFilter(EntryFilter):
    class Meta:
        model = models.News
        fields = ['by_following']

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class EventFilter(EntryFilter):
    rsvp_by = django_filters.CharFilter(method='filter_rsvp_by')
    begin_date = django_filters.CharFilter(method='filter_begin_date')
    end_date = django_filters.CharFilter(method='filter_end_date')
    order_by = EntryOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('date', 'date'),
            ('like_count', 'like_count'),
        ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.Event
        fields = []

    def filter_rsvp_by(self, qs, name, value):
        return qs.filter(
            id__in=models.User.objects.get(
                id=from_global_id(value)[1]).rsvp_for_event.all())

    def filter_begin_date(self, qs, name, value):
        return qs.filter(date__gte=value)

    def filter_end_date(self, qs, name, value):
        return qs.filter(date__lt=value)

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class PostFilter(EntryFilter):
    class Meta:
        model = models.Post
        fields = []

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class ActivityFilter(EntryFilter):
    active = django_filters.BooleanFilter(method='filter_active')
    order_by = EntryOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('date', 'date'),
            ('active', 'active'),
        ))

    class Meta:
        model = models.Activity
        fields = []

    def filter_active(self, qs, name, value):
        return qs.filter(active=value)

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class CommentFilter(django_filters.FilterSet):
    parent = django_filters.CharFilter(
        method='filter_parent',
        required=True,
    )
    user = django_filters.CharFilter(method='filter_user')
    scratch = django_filters.CharFilter(method='filter_scratch')

    order_by = EntryOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))

    class Meta:
        model = models.Comment
        fields = []

    def filter_parent(self, qs, name, value):
        if not (self.request.user.is_superuser
                or models.User.objects.get(id=self.request.user.id).can_see(
                    models.Entry.objects.get(id=from_global_id(value)[1]))):
            raise GraphQLError('You do not have sufficient permission')
        return qs.filter(parent_id=from_global_id(value)[1])

    def filter_user(self, qs, name, value):
        return qs.filter(user_id=from_global_id(value)[1])

    def filter_scratch(self, qs, name, value):
        if not (self.request.user.is_superuser
                or self.request.user.id == int(from_global_id(value)[1])):
            raise GraphQLError('You do not have sufficient permission')
        return qs.filter(scratch=value)


class ChannelOrderingFilter(django_filters.OrderingFilter):
    class Meta:
        model = models.Channel
        fields = []

    def __init__(self, *args, **kwargs):
        super(ChannelOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['messaged_last', '-messaged_last']:
                if v in value:
                    try:
                        qs = qs.annotate(
                            messaged_last=Subquery(
                                models.MessageChannel.objects.filter(
                                    Q(target=OuterRef('id'))).order_by(
                                        '-created').values('created')
                                [:1])).order_by(v)
                    except FieldError:
                        raise GraphQLError(
                            'You do not have sufficient permission')
                        value.remove(v)

        return super(ChannelOrderingFilter, self).filter(qs, value)


class ChannelFilter(django_filters.FilterSet):
    order_by = ChannelOrderingFilter(
        fields=(
            ('created', 'created'),
            ('messaged_last', 'messaged_last'),
        ))


class MessageDirectFilter(django_filters.FilterSet):
    with_user = django_filters.CharFilter(method='filter_with_user')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))

    def filter_with_user(self, qs, name, value):
        return qs.filter(
            Q(user_id=from_global_id(value)[1])
            | Q(target_id=from_global_id(value)[1]))


class MessageChannelFilter(django_filters.FilterSet):
    with_channel = django_filters.CharFilter(method='filter_with_channel')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))

    def filter_with_channel(self, qs, name, value):
        return qs.filter(Q(target_id=from_global_id(value)[1]))


# --- Organization Category ------------------------------------------------- #


class OrganizationCategoryNode(DjangoObjectType):
    class Meta:
        model = models.OrganizationCategory
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        return queryset


# --- Deposit Category ------------------------------------------------------ #


class ExchangeCategoryNode(DjangoObjectType):
    class Meta:
        model = models.ExchangeCategory
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        return queryset


# --- Deposit --------------------------------------------------------------- #


class DepositNode(DjangoObjectType):
    class Meta:
        model = models.Deposit
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset
        return queryset.filter(user=info.context.user)


# --- Withdrawal ------------------------------------------------------------ #


class WithdrawalNode(DjangoObjectType):
    class Meta:
        model = models.Withdrawal
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset
        return queryset.filter(user=info.context.user)


# --- Investment ------------------------------------------------------------ #


class InvestmentNode(DjangoObjectType):
    donation_amount = DjangoFilterConnectionField(
        lambda: InvestmentDonationNode,
        filterset_class=InvestmentDonationFilter,
    )

    class Meta:
        model = models.Investment
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset
        return queryset.filter(user=info.context.user)

    def resolve_donation_amount(self, *args, **kwargs):
        return self.investmentdonation_set.all()


class InvestmentDonationNode(DjangoObjectType):
    class Meta:
        model = models.InvestmentDonation
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset
        return queryset.filter(investment__user=info.context.user)


# --- Entry ----------------------------------------------------------------- #


class EntryNode(DjangoObjectType):
    user = graphene.Field(lambda: UserNode)
    description = graphene.String()
    comments = DjangoFilterConnectionField(
        lambda: CommentNode,
        filterset_class=CommentFilter,
    )
    comment_count = graphene.Int()
    comment_count_recursive = graphene.Int()
    commenter_recursive = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    like = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    like_count = graphene.Int()
    bookmark = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    mention = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    scratch = graphene.String()
    entry_type = graphene.String()
    root = graphene.Field(lambda: EntryNode)

    class Meta:
        model = models.Entry
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    def resolve_user(self, *args, **kwargs):
        return get_submodel(self).objects.get(id=self.id).user.user

    def resolve_description(self, *args, **kwargs):
        return self.resolve_description()

    def resolve_comment_count(self, *args, **kwargs):
        return models.Comment.objects.filter(parent=self).count()

    def resolve_comment_count_recursive(self, *args, **kwargs):

        count = 0
        stack = list(models.Comment.objects.filter(parent=self))

        while len(stack) > 0:
            entry = stack.pop()
            count += 1
            stack += list(models.Comment.objects.filter(parent=entry))

        return count

    def resolve_commenter_recursive(self, *args, **kwargs):
        comments = []
        stack = list(models.Comment.objects.filter(parent=self))

        while len(stack) > 0:
            comments.append(stack.pop())
            stack += list(models.Comment.objects.filter(parent=comments[-1]))

        commenters = []
        for comment in sorted(comments, key=lambda x: x.created, reverse=True):
            if comment.user not in commenters:
                commenters.append(comment.user)

        return commenters

    def resolve_like(self, info, *args, **kwargs):
        if not info.context.user.is_superuser:
            return self.like.filter(id=info.context.user.id)
        return self.like

    def resolve_like_count(self, *args, **kwargs):
        return self.like.count()

    def resolve_bookmark(self, *args, **kwargs):
        return self.bookmark

    def resolve_mention(self, *args, **kwargs):
        return self.mention

    def resolve_scratch(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or self.user.id == info.context.user.id):
            return None
        return self.scratch

    def resolve_entry_type(self, *args, **kwargs):
        return get_submodel(self).__name__

    def resolve_root(self, *args, **kwargs):
        if models.Comment.objects.filter(id=self.id).exists():
            return models.Comment.objects.get(id=self.id).get_root()
        return self

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')

        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            (Q(donation__isnull=False) &
             (Q(donation__private=False)
              | Q(donation__user_id=info.context.user.id)
              | Q(donation__target_id=info.context.user.id)))
            | (Q(reward__isnull=False) &
               (Q(reward__private=False)
                | Q(reward__user_id=info.context.user.id)
                | Q(reward__target_id=info.context.user.id)))
            | (Q(donation__isnull=True) & Q(reward__isnull=True)))


# --- Donation -------------------------------------------------------------- #


class DonationNode(EntryNode):
    amount = graphene.Int()
    investment_amount = DjangoFilterConnectionField(
        lambda: InvestmentDonationNode,
        filterset_class=InvestmentDonationFilter,
    )

    class Meta:
        model = models.Donation
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    def resolve_amount(self, *args, **kwargs):
        return self.amount

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')

        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            Q(private=False) | Q(user__id=info.context.user.id)
            | Q(target_id=info.context.user.id)).distinct()

    def resolve_investment_amount(self, *args, **kwargs):
        return self.investmentdonation_set.all()


class DonationCreate(Mutation):
    class Meta:
        model = models.Donation

    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        target = graphene.ID(required=True)
        amount = graphene.Int(required=True)
        private = graphene.Boolean()
        score = graphene.Int()

    donation = graphene.Field(DonationNode)

    def mutate(
            self,
            info,
            user,
            description,
            target,
            amount,
            private=False,
            score=0,
    ):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        try:
            assert len(description) > 0
            assert amount > 0
            assert amount <= settings.MAX_TRANSFER
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        user_obj = models.Person.objects.get(pk=from_global_id(user)[1])
        target_obj = models.Organization.objects.get(
            pk=from_global_id(target)[1])

        try:
            assert user_obj.balance() - amount >= 0
        except AssertionError:
            raise GraphQLError('Balance would be below zero')

        donation = models.Donation.objects.create(
            user=user_obj,
            description=description,
            target=target_obj,
            amount=amount,
            private=private,
            score=score,
        )

        return DonationCreate(donation=donation)


# --- Reward ----------------------------------------------------------- #


class RewardNode(EntryNode):
    amount = graphene.Int()

    class Meta:
        model = models.Reward
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    def resolve_amount(self, *args, **kwargs):
        return self.amount

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')

        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            Q(private=False) | Q(user__id=info.context.user.id)
            | Q(target_id=info.context.user.id)).distinct()


class RewardCreate(Mutation):
    class Meta:
        model = models.Reward

    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        target = graphene.ID(required=True)
        amount = graphene.Int(required=True)
        private = graphene.Boolean()
        related_activity = graphene.ID()
        score = graphene.Int()
        scratch = graphene.String()

    reward = graphene.Field(RewardNode)

    def mutate(
            self,
            info,
            user,
            description,
            target,
            amount,
            private=False,
            scratch=None,
            related_activity=None,
            score=0,
    ):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        try:
            assert len(description) > 0
            assert amount > 0
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        user_obj = models.Bot.objects.get(pk=from_global_id(user)[1])
        target_obj = models.Person.objects.get(pk=from_global_id(target)[1])

        try:
            assert user_obj.balance() - amount >= 0
        except AssertionError:
            raise GraphQLError('Balance would be below zero')

        if related_activity:
            related_activity = models.Activity.objects.get(
                id=from_global_id(related_activity)[1])

        reward = models.Reward.objects.create(
            user=user_obj,
            description=description,
            target=target_obj,
            amount=amount,
            private=private,
            related_activity=related_activity,
            scratch=scratch,
            score=score,
        )

        return RewardCreate(reward=reward)


# --- News ------------------------------------------------------------------ #


class NewsNode(EntryNode):
    class Meta:
        model = models.News
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        return queryset


class NewsCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        title = graphene.String(required=True)
        image = Upload()
        score = graphene.Int()
        link = graphene.String()

    news = graphene.Field(NewsNode)

    def mutate(
            self,
            info,
            user,
            description,
            title,
            image='',
            link='',
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Organization.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        news = models.News.objects.create(
            user=models.Organization.objects.get(pk=from_global_id(user)[1]),
            description=description,
            title=title,
            link=link,
            image='',
            score=score,
        )

        if link:
            news.link = link

        if image:
            news.image = models.store_image(
                image,
                os.path.join('news', to_global_id('EntryNode', news.id)),
            )

        news.save()
        return NewsCreate(news=news)


class NewsUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        description = graphene.String()
        title = graphene.String()
        link = graphene.String()
        image = Upload()
        score = graphene.Int()

    news = graphene.Field(NewsNode)

    def mutate(
            self,
            info,
            id,
            user=None,
            description='',
            title='',
            link='',
            image='',
            score=None,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == models.News.objects.get(
                    id=from_global_id(id)[1]).user.id and
                 (not user
                  or int(from_global_id(user)[1]) == info.context.user.id))):
            raise GraphQLError('You do not have sufficient permission')

        news = models.News.objects.get(pk=from_global_id(id)[1])
        if user:
            news.user = models.Organization.objects.get(
                pk=from_global_id(user)[1])
        if description:
            news.description = description
        if title:
            news.title = title
        if link:
            news.link = link
        if image:
            news.image = models.store_image(
                image,
                os.path.join('news', to_global_id('EntryNode', id)),
            )
        if type(score) == int:
            news.score = score

        news.save()
        return NewsUpdate(news=news)


# --- Event ----------------------------------------------------------------- #


class EventNode(EntryNode):
    rsvp = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    rsvp_count = graphene.Int()

    class Meta:
        model = models.Event
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    def resolve_rsvp(self, *args, **kwargs):
        return self.rsvp

    def resolve_rsvp_count(self, *args, **kwargs):
        return self.rsvp.count()

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        return queryset


class EventCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        title = graphene.String(required=True)
        date = graphene.String(required=True)
        duration = graphene.Int(required=True)
        image = Upload()
        address = graphene.String()
        link = graphene.String()
        virtual = graphene.Boolean()
        score = graphene.Int()

    event = graphene.Field(EventNode)

    def mutate(
            self,
            info,
            user,
            description,
            title,
            date,
            duration,
            image='',
            address='',
            link='',
            virtual=False,
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Organization.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        event = models.Event.objects.create(
            user=models.Organization.objects.get(pk=from_global_id(user)[1]),
            description=description,
            title=title,
            image='',
            date=dateutil.parser.parse(date),
            duration=duration,
            virtual=virtual,
            score=score,
        )

        if address:
            event.address = address
        if link:
            event.link = link

        if image:
            event.image = models.store_image(
                image,
                os.path.join('event', to_global_id('EntryNode', event.id)),
            )

        event.save()
        return EventCreate(event=event)


class EventUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        description = graphene.String()
        title = graphene.String()
        link = graphene.String()
        image = Upload()
        date = graphene.String()
        duration = graphene.Int()
        address = graphene.String()
        virtual = graphene.Boolean()
        score = graphene.Int()

    event = graphene.Field(EventNode)

    def mutate(
            self,
            info,
            id,
            user=None,
            description='',
            title='',
            link='',
            image='',
            date='',
            duration=None,
            address='',
            virtual=None,
            score=None,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == models.Event.objects.get(
                    id=from_global_id(id)[1]).user.id and
                 (not user
                  or int(from_global_id(user)[1]) == info.context.user.id))):
            raise GraphQLError('You do not have sufficient permission')

        event = models.Event.objects.get(pk=from_global_id(id)[1])
        if user:
            event.user = models.Organization.objects.get(
                pk=from_global_id(user)[1])
        if description:
            event.description = description
        if title:
            event.title = title
        if link:
            event.link = link
        if image:
            event.image = models.store_image(
                image,
                os.path.join('event', to_global_id('EntryNode', id)),
            )
        if date:
            event.date = date
        if type(duration) == int:
            event.duration = duration
        if address:
            event.address = address
        if type(virtual) == bool:
            event.virtual = virtual
        if type(score) == int:
            event.score = score

        event.save()
        return EventUpdate(event=event)


# --- Ibis User ------------------------------------------------------------- #


class UserNode(GeneralUserNode):
    name = graphene.String()
    balance = graphene.Int()
    following = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    follower = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    following_count = graphene.Int()
    follower_count = graphene.Int()
    following_count_person = graphene.Int()
    following_count_organization = graphene.Int()
    follower_count_person = graphene.Int()
    follower_count_organization = graphene.Int()
    event_rsvp_count = graphene.Int()
    scratch = graphene.String()
    user_type = graphene.String()
    messages = DjangoFilterConnectionField(
        lambda: MessageDirectNode,
        filterset_class=MessageDirectFilter,
    )

    class Meta:
        model = models.User
        exclude = ['email', 'password']
        filter_fields = []
        interfaces = (UserNodeInterface, )

    def resolve_name(self, *args, **kwargs):
        return str(self)

    def resolve_balance(self, *args, **kwargs):
        return self.balance()

    def resolve_following_count(self, *args, **kwargs):
        return self.following.count()

    def resolve_follower_count(self, *args, **kwargs):
        return self.follower.count()

    def resolve_following_count_person(self, *args, **kwargs):
        return len([x for x in self.following.all() if hasattr(x, 'person')])

    def resolve_following_count_organization(self, *args, **kwargs):
        return len(
            [x for x in self.following.all() if hasattr(x, 'organization')])

    def resolve_follower_count_person(self, *args, **kwargs):
        return len([x for x in self.follower.all() if hasattr(x, 'person')])

    def resolve_follower_count_organization(self, *args, **kwargs):
        return len(
            [x for x in self.follower.all() if hasattr(x, 'organization')])

    def resolve_event_rsvp_count(self, *args, **kwargs):
        return self.rsvp_for_event.filter(date__gte=localtime()).count()

    def resolve_scratch(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or self.id == info.context.user.id):
            return None
        return self.scratch

    def resolve_user_type(self, *args, **kwargs):
        return get_submodel(self).__name__

    def resolve_messages(self, *args, **kwargs):
        return models.MessageDirect.objects.filter(
            Q(user=self.id) | Q(target=self.id))

    @classmethod
    def get_queryset(cls, queryset, info, hide_inactive=True):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        if hide_inactive:
            return queryset.filter(is_active=True)
        return queryset

    @classmethod
    def get_node(cls, info, id):
        queryset = cls.get_queryset(
            cls._meta.model.objects,
            info,
            hide_inactive=False,
        )
        try:
            return queryset.get(pk=id)
        except cls._meta.model.DoesNotExist:
            return None


# --- Organization ---------------------------------------------------------- #


class OrganizationNode(UserNode):

    fundraised = graphene.Int()
    news_count = graphene.Int()
    event_count = graphene.Int()
    donation_received_count = graphene.Int()
    has_recent_entry = graphene.Boolean()
    recent_response_rate = graphene.Float()

    class Meta:
        model = models.Organization
        exclude = ['email', 'password']
        filter_fields = []
        interfaces = (UserNodeInterface, )

    def resolve_fundraised(self, *args, **kwargs):
        return self.fundraised()

    def resolve_news_count(self, *args, **kwargs):
        return models.News.objects.filter(user__id=self.id).count()

    def resolve_event_count(self, *args, **kwargs):
        return models.Event.objects.filter(
            user__id=self.id,
            date__gte=localtime(),
        ).count()

    def resolve_donation_received_count(self, info, *args, **kwargs):
        return models.Donation.objects.filter(target=self).count()

    def resolve_has_recent_entry(self, info, *args, **kwargs):
        return self.has_recent_entry()

    def resolve_recent_response_rate(self, info, *args, **kwargs):
        return self.recent_response_rate()


class OrganizationUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        username = graphene.String()
        email = graphene.String()
        category = graphene.ID()
        description = graphene.String()
        first_name = graphene.String()
        last_name = graphene.String()
        link = graphene.String()
        privacy_donation = graphene.Boolean()
        privacy_reward = graphene.Boolean()
        privacy_deposit = graphene.Boolean()
        avatar = Upload()
        banner = Upload()
        score = graphene.Int()

    organization = graphene.Field(OrganizationNode)

    def mutate(
            self,
            info,
            id,
            username='',
            email='',
            category=None,
            description='',
            first_name=None,
            last_name=None,
            link='',
            privacy_donation=None,
            privacy_reward=None,
            privacy_deposit=None,
            avatar=None,
            banner=None,
            score=0,
    ):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(id)[1])):
            raise GraphQLError('You do not have sufficient permission')

        organization = models.Organization.objects.get(
            pk=from_global_id(id)[1])
        if username:
            organization.username = username
        if email:
            organization.email = email
        if type(first_name) == str:
            organization.first_name = first_name
        if type(last_name) == str:
            organization.last_name = last_name
        if category:
            organization.category = models.OrganizationCategory.objects.get(
                pk=from_global_id(category)[1])
        if description:
            organization.description = description
        if link:
            organization.link = link
        if type(privacy_donation) == bool:
            organization.privacy_donation = privacy_donation
        if type(privacy_reward) == bool:
            organization.privacy_reward = privacy_reward
        if type(privacy_deposit) == bool:
            organization.privacy_deposit = privacy_deposit
        if avatar:
            organization.avatar = models.store_image(
                avatar,
                os.path.join('avatar', to_global_id('UserNode', id)),
                thumbnail_size=AVATAR_SIZE,
            )
        if banner:
            organization.banner = models.store_image(
                banner,
                os.path.join('banner', to_global_id('UserNode', id)),
            )

        organization.save()
        return OrganizationUpdate(organization=organization)


# --- Person ---------------------------------------------------------------- #


class PersonNode(UserNode):

    donated = graphene.Int()
    donation_count = graphene.Int()
    post_count = graphene.Int()
    reward_received_count = graphene.Int()
    phone_number = graphene.String()

    class Meta:
        model = models.Person
        exclude = ['email', 'password']
        filter_fields = []
        interfaces = (UserNodeInterface, )

    def resolve_donated(self, *args, **kwargs):
        return self.donated()

    def resolve_donation_count(self, info, *args, **kwargs):
        return self.donation_set.count()

    def resolve_post_count(self, *args, **kwargs):
        return models.Post.objects.filter(user__id=self.id).count()

    def resolve_reward_received_count(self, info, *args, **kwargs):
        return models.Reward.objects.filter(target=self).count()

    def resolve_phone_number(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser
                or info.context.user.id == self.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.phone_number


class PersonUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        username = graphene.String()
        email = graphene.String()
        description = graphene.String()
        first_name = graphene.String()
        last_name = graphene.String()
        privacy_donation = graphene.Boolean()
        privacy_reward = graphene.Boolean()
        privacy_deposit = graphene.Boolean()
        avatar = Upload()
        score = graphene.Int()

    person = graphene.Field(PersonNode)

    def mutate(
            self,
            info,
            id,
            username='',
            email='',
            description='',
            first_name='',
            last_name='',
            privacy_donation=None,
            privacy_reward=None,
            privacy_deposit=None,
            avatar=None,
            score=None,
    ):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(id)[1])):
            raise GraphQLError('You do not have sufficient permission')

        person = models.Person.objects.get(pk=from_global_id(id)[1])
        if username:
            person.username = username
        if email:
            person.email = email
        if description:
            person.description = description
        if first_name:
            person.first_name = first_name
        if last_name:
            person.first_name = last_name
        if type(privacy_donation) == bool:
            person.privacy_donation = privacy_donation
        if type(privacy_reward) == bool:
            person.privacy_reward = privacy_reward
        if type(privacy_deposit) == bool:
            person.privacy_deposit = privacy_deposit
        if avatar:
            person.avatar = models.store_image(
                avatar,
                os.path.join('avatar', to_global_id('UserNode', id)),
                thumbnail_size=AVATAR_SIZE,
            )
        if type(score) == int:
            person.score = score
        person.save()
        return PersonUpdate(person=person)


# --- Bot ---------------------------------------------------------------- #


class BotNode(UserNode):

    rewarded = graphene.Int()
    reward_count = graphene.Int()
    activity_count = graphene.Int()

    class Meta:
        model = models.Bot
        exclude = ['email', 'password']
        filter_fields = []
        interfaces = (UserNodeInterface, )

    def resolve_rewarded(self, *args, **kwargs):
        return self.rewarded()

    def resolve_reward_count(self, info, *args, **kwargs):
        return self.reward_set.count()

    def resolve_activity_count(self, info, *args, **kwargs):
        return self.activity_set.count()


class BotUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        username = graphene.String()
        email = graphene.String()
        description = graphene.String()
        first_name = graphene.String()
        last_name = graphene.String()
        privacy_donation = graphene.Boolean()
        privacy_reward = graphene.Boolean()
        privacy_deposit = graphene.Boolean()
        avatar = Upload()
        tank = graphene.Int()
        scratch = graphene.String()
        score = graphene.Int()

    bot = graphene.Field(BotNode)

    def mutate(
            self,
            info,
            id,
            username='',
            email='',
            description='',
            first_name='',
            last_name='',
            privacy_donation=None,
            privacy_reward=None,
            privacy_deposit=None,
            avatar=None,
            tank=None,
            scratch=None,
            score=None,
    ):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(id)[1])):
            raise GraphQLError('You do not have sufficient permission')

        bot = models.Bot.objects.get(pk=from_global_id(id)[1])
        if username:
            bot.username = username
        if email:
            bot.email = email
        if description:
            bot.description = description
        if first_name:
            bot.first_name = first_name
        if last_name:
            bot.first_name = last_name
        if type(privacy_donation) == bool:
            bot.privacy_donation = privacy_donation
        if type(privacy_reward) == bool:
            bot.privacy_reward = privacy_reward
        if type(privacy_deposit) == bool:
            bot.privacy_deposit = privacy_deposit
        if avatar:
            bot.avatar = models.store_image(
                avatar,
                os.path.join('avatar', to_global_id('UserNode', id)),
                thumbnail_size=AVATAR_SIZE,
            )
        if type(tank) == int:
            bot.tank = tank
        if type(scratch) == str:
            bot.scratch = scratch
        if type(score) == int:
            bot.score = score
        bot.save()
        return BotUpdate(bot=bot)


# --- Post ------------------------------------------------------------------ #


class PostNode(EntryNode):
    class Meta:
        model = models.Post
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        return queryset


class PostCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        title = graphene.String(required=True)
        description = graphene.String(required=True)
        score = graphene.Int()

    post = graphene.Field(PostNode)

    def mutate(
            self,
            info,
            user,
            title,
            description,
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Person.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        post = models.Post.objects.create(
            user=models.Person.objects.get(pk=from_global_id(user)[1]),
            title=title,
            description=description,
            score=score,
        )

        return PostCreate(post=post)


# --- Activity -------------------------------------------------------------- #


class ActivityNode(EntryNode):
    class Meta:
        model = models.Activity
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        return queryset


class ActivityCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        title = graphene.String(required=True)
        description = graphene.String(required=True)
        active = graphene.Boolean()
        reward_min = graphene.Int()
        reward_range = graphene.Int()
        scratch = graphene.String()
        score = graphene.Int()

    activity = graphene.Field(ActivityNode)

    def mutate(
            self,
            info,
            user,
            title,
            description,
            active,
            reward_min=None,
            reward_range=None,
            scratch=None,
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1])) and
                models.Bot.objects.filter(id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        activity = models.Activity.objects.create(
            user=models.Bot.objects.get(pk=from_global_id(user)[1]),
            title=title,
            active=active,
            description=description,
            score=score,
        )

        if type(reward_min) == int:
            activity.reward_min = reward_min
        if type(reward_range) == int:
            activity.reward_range = reward_range
        if type(scratch) == str:
            activity.scratch = scratch
        activity.save()

        return ActivityCreate(activity=activity)


class ActivityUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        title = graphene.String()
        description = graphene.String()
        active = graphene.Boolean()
        reward_min = graphene.Int()
        reward_range = graphene.Int()
        scratch = graphene.String()
        score = graphene.Int()

    activity = graphene.Field(ActivityNode)

    def mutate(
            self,
            info,
            id,
            user=None,
            title=None,
            description=None,
            active=None,
            reward_min=None,
            reward_range=None,
            scratch=None,
            score=None,
    ):

        if not (info.context.user.is_superuser or
                (info.context.user.id == models.Activity.objects.get(
                    id=from_global_id(id)[1]).user.id and
                 (not user
                  or int(from_global_id(user)[1]) == info.context.user.id))):
            raise GraphQLError('You do not have sufficient permission')

        activity = models.Activity.objects.get(pk=from_global_id(id)[1])
        if user:
            activity.user = models.Bot.objects.get(pk=from_global_id(user)[1])
        if description:
            activity.description = description
        if title:
            activity.title = title
        if type(active) == bool:
            activity.active = active
        if type(reward_min) == int:
            activity.reward_min = reward_min
        if type(reward_range) == int:
            activity.reward_range = reward_range
        if type(scratch) == str:
            activity.scratch = scratch
        if type(score) == int:
            activity.score = score

        activity.save()
        return ActivityUpdate(activity=activity)


# --- Comment --------------------------------------------------------------- #


class CommentNode(EntryNode):
    class Meta:
        model = models.Comment
        filter_fields = []
        interfaces = (EntryNodeInterface, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')
        return queryset

    @classmethod
    def get_node(cls, info, id):
        queryset = cls.get_queryset(cls._meta.model.objects, info)
        try:
            comment = queryset.get(pk=id)
            if not (info.context.user.is_superuser or models.User.objects.get(
                    id=info.context.user.id).can_see(comment)):
                raise GraphQLError('You do not have sufficient permission')
            return comment
        except cls._meta.model.DoesNotExist:
            return None


class CommentCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        parent = graphene.ID(required=True)
        scratch = graphene.String()

    comment = graphene.Field(CommentNode)

    def mutate(
            self,
            info,
            user,
            description,
            parent,
            scratch=None,
    ):
        parent_obj = models.Entry.objects.get(pk=from_global_id(parent)[1])

        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1])
                 and hasattr(info.context.user, 'user')
                 and info.context.user.user.can_see(parent_obj))):
            raise GraphQLError('You do not have sufficient permission')

        comment = models.Comment.objects.create(
            user=models.User.objects.get(pk=from_global_id(user)[1]),
            description=description,
            parent=parent_obj,
            scratch=scratch,
        )

        return CommentCreate(comment=comment)


# --- Channel ----------------------------------------------------------------- #


class ChannelNode(DjangoObjectType):
    class Meta:
        model = models.Channel
        filter_fields = []
        interfaces = (relay.Node, )

    member = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    subscriber = DjangoFilterConnectionField(
        lambda: UserNode,
        filterset_class=UserFilter,
    )
    messages = DjangoFilterConnectionField(
        lambda: MessageChannelNode,
        filterset_class=MessageChannelFilter,
    )

    def resolve_member(self, *args, **kwargs):
        return self.member

    def resolve_subscriber(self, *args, **kwargs):
        return self.subscriber

    def resolve_messages(self, *args, **kwargs):
        return models.MessageChannel.objects.filter(target=self.id)

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated and not settings.PUBLIC_READ:
            raise GraphQLError('You are not logged in')

        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            Q(member__isnull=True)
            | Q(
                id__in=models.User.objects.get(
                    id=info.context.user.id).channel_set.all())).distinct()


# --- Direct Message -------------------------------------------------------- #


class MessageDirectNode(DjangoObjectType):
    class Meta:
        model = models.MessageDirect
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            Q(user=info.context.user) | Q(target=info.context.user))


class MessageDirectCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)
        description = graphene.String(required=True)

    message_direct = graphene.Field(MessageDirectNode)

    def mutate(self, info, user, target, description):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        user_obj = models.User.objects.get(pk=from_global_id(user)[1])
        target_obj = models.User.objects.get(pk=from_global_id(target)[1])

        message_direct = models.MessageDirect.objects.create(
            user=user_obj,
            target=target_obj,
            description=description,
        )

        return MessageDirectCreate(message_direct=message_direct)


# --- MessageChannel ---------------------------------------------------------- #


class MessageChannelNode(DjangoObjectType):
    class Meta:
        model = models.MessageChannel
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            Q(target__member__isnull=True)
            | Q(
                target__id__in=models.User.objects.get(
                    id=info.context.user.id).channel_set.all())).distinct()


class MessageChannelCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)
        description = graphene.String(required=True)

    message_channel = graphene.Field(MessageChannelNode)

    def mutate(self, info, user, target, description):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        user_obj = models.User.objects.get(pk=from_global_id(user)[1])
        target_obj = models.Channel.objects.get(pk=from_global_id(target)[1])

        if not (target_obj.member.count() == 0
                or target_obj.member.filter(pk=user_obj.pk).exists()):
            raise GraphQLError('You do not have sufficient permission')

        message_channel = models.MessageChannel.objects.create(
            user=user_obj,
            target=target_obj,
            description=description,
        )

        return MessageChannelCreate(message_channel=message_channel)


# --- Follow ---------------------------------------------------------------- #


class FollowMutation(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)

    state = graphene.Boolean()

    @classmethod
    def mutate(cls, info, operation, user, target):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        user_obj = models.User.objects.get(pk=from_global_id(user)[1])
        target_obj = models.User.objects.get(pk=from_global_id(target)[1])
        getattr(user_obj.following, operation)(target_obj)
        user_obj.save()
        return FollowMutation(
            state=user_obj.following.filter(id=target_obj.id).exists())


class FollowCreate(FollowMutation):
    def mutate(self, info, **kwargs):
        return FollowMutation.mutate(info, 'add', **kwargs)


class FollowDelete(FollowMutation):
    def mutate(self, info, **kwargs):
        return FollowMutation.mutate(info, 'remove', **kwargs)


# --- Likes ----------------------------------------------------------------- #


class LikeMutation(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)

    state = graphene.Boolean()

    @classmethod
    def mutate(cls, info, operation, user, target):
        user_obj = models.User.objects.get(pk=from_global_id(user)[1])
        entry_obj = models.Entry.objects.get(pk=from_global_id(target)[1])

        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1])
                 and hasattr(info.context.user, 'user')
                 and info.context.user.user.can_see(entry_obj))):
            raise GraphQLError('You do not have sufficient permission')

        getattr(entry_obj.like, operation)(user_obj)
        entry_obj.save()
        return LikeMutation(
            state=entry_obj.like.filter(id=user_obj.id).exists())


class LikeCreate(LikeMutation):
    def mutate(self, info, **kwargs):
        return LikeMutation.mutate(info, 'add', **kwargs)


class LikeDelete(LikeMutation):
    def mutate(self, info, **kwargs):
        return LikeMutation.mutate(info, 'remove', **kwargs)


# --- Bookmarks ------------------------------------------------------------- #


class BookmarkMutation(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)

    state = graphene.Boolean()

    @classmethod
    def mutate(cls, info, operation, user, target):
        user_obj = models.User.objects.get(pk=from_global_id(user)[1])
        entry_obj = models.Entry.objects.get(pk=from_global_id(target)[1])

        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1])
                 and hasattr(info.context.user, 'user')
                 and info.context.user.user.can_see(entry_obj))):
            raise GraphQLError('You do not have sufficient permission')

        getattr(entry_obj.bookmark, operation)(user_obj)
        entry_obj.save()
        return BookmarkMutation(
            state=entry_obj.bookmark.filter(id=user_obj.id).exists())


class BookmarkCreate(BookmarkMutation):
    def mutate(self, info, **kwargs):
        return BookmarkMutation.mutate(info, 'add', **kwargs)


class BookmarkDelete(BookmarkMutation):
    def mutate(self, info, **kwargs):
        return BookmarkMutation.mutate(info, 'remove', **kwargs)


# --- RSVPs ----------------------------------------------------------------- #


class RsvpMutation(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)

    state = graphene.Boolean()

    @classmethod
    def mutate(cls, info, operation, user, target):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        user_obj = models.User.objects.get(pk=from_global_id(user)[1])
        event_obj = models.Event.objects.get(pk=from_global_id(target)[1])
        getattr(event_obj.rsvp, operation)(user_obj)
        event_obj.save()
        return RsvpMutation(
            state=event_obj.rsvp.filter(id=user_obj.id).exists())


class RsvpCreate(RsvpMutation):
    def mutate(self, info, **kwargs):
        return RsvpMutation.mutate(info, 'add', **kwargs)


class RsvpDelete(RsvpMutation):
    def mutate(self, info, **kwargs):
        return RsvpMutation.mutate(info, 'remove', **kwargs)


# --- Subscription ---------------------------------------------------------- #


class SubscriptionMutation(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)

    state = graphene.Boolean()

    @classmethod
    def mutate(cls, info, operation, user, target):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        user_obj = models.User.objects.get(pk=from_global_id(user)[1])
        target_obj = models.Channel.objects.get(pk=from_global_id(target)[1])
        getattr(target_obj.subscriber, operation)(user_obj)
        target_obj.save()
        return SubscriptionMutation(
            state=target_obj.subscriber.filter(id=user_obj.id).exists())


class SubscriptionCreate(SubscriptionMutation):
    def mutate(self, info, **kwargs):
        return SubscriptionMutation.mutate(info, 'add', **kwargs)


class SubscriptionDelete(SubscriptionMutation):
    def mutate(self, info, **kwargs):
        return SubscriptionMutation.mutate(info, 'remove', **kwargs)


# --------------------------------------------------------------------------- #


class Query(object):

    organization_category = relay.Node.Field(OrganizationCategoryNode)
    exchange_category = relay.Node.Field(ExchangeCategoryNode)
    user = UserNodeInterface.Field(UserNode)
    organization = UserNodeInterface.Field(OrganizationNode)
    person = UserNodeInterface.Field(PersonNode)
    bot = UserNodeInterface.Field(BotNode)
    withdrawal = relay.Node.Field(WithdrawalNode)
    entry = EntryNodeInterface.Field(EntryNode)
    deposit = relay.Node.Field(DepositNode)
    investment = relay.Node.Field(InvestmentNode)
    donation = EntryNodeInterface.Field(DonationNode)
    reward = EntryNodeInterface.Field(RewardNode)
    news = EntryNodeInterface.Field(NewsNode)
    event = EntryNodeInterface.Field(EventNode)
    post = EntryNodeInterface.Field(PostNode)
    activity = EntryNodeInterface.Field(ActivityNode)
    comment = EntryNodeInterface.Field(CommentNode)
    channel = relay.Node.Field(ChannelNode)
    message_direct = EntryNodeInterface.Field(MessageDirectNode)
    message_channel = EntryNodeInterface.Field(MessageChannelNode)

    all_organization_categories = DjangoFilterConnectionField(
        OrganizationCategoryNode)
    all_exchange_categories = DjangoFilterConnectionField(ExchangeCategoryNode)
    all_users = DjangoFilterConnectionField(
        UserNode,
        filterset_class=UserFilter,
    )
    all_people = DjangoFilterConnectionField(
        PersonNode,
        filterset_class=PersonFilter,
    )
    all_bots = DjangoFilterConnectionField(
        BotNode,
        filterset_class=UserFilter,
    )
    all_organizations = DjangoFilterConnectionField(
        OrganizationNode,
        filterset_class=UserFilter,
    )
    all_deposits = DjangoFilterConnectionField(
        DepositNode,
        filterset_class=DepositFilter,
    )
    all_withdrawals = DjangoFilterConnectionField(
        WithdrawalNode,
        filterset_class=WithdrawalFilter,
    )
    all_investments = DjangoFilterConnectionField(
        InvestmentNode,
        filterset_class=InvestmentFilter,
    )
    all_entries = DjangoFilterConnectionField(
        EntryNode,
        filterset_class=EntryFilter,
    )
    all_donations = DjangoFilterConnectionField(
        DonationNode,
        filterset_class=DonationFilter,
    )
    all_rewards = DjangoFilterConnectionField(
        RewardNode,
        filterset_class=RewardFilter,
    )
    all_news = DjangoFilterConnectionField(
        NewsNode,
        filterset_class=NewsFilter,
    )
    all_events = DjangoFilterConnectionField(
        EventNode,
        filterset_class=EventFilter,
    )
    all_posts = DjangoFilterConnectionField(
        PostNode,
        filterset_class=PostFilter,
    )
    all_activities = DjangoFilterConnectionField(
        ActivityNode,
        filterset_class=ActivityFilter,
    )
    all_comments = DjangoFilterConnectionField(
        CommentNode,
        filterset_class=CommentFilter,
    )
    all_channels = DjangoFilterConnectionField(
        ChannelNode,
        filterset_class=ChannelFilter,
    )
    all_messages_direct = DjangoFilterConnectionField(
        MessageDirectNode,
        filterset_class=MessageDirectFilter,
    )
    all_messages_channel = DjangoFilterConnectionField(
        MessageChannelNode,
        filterset_class=MessageChannelFilter,
    )


class Mutation(graphene.ObjectType):
    create_donation = DonationCreate.Field()
    create_reward = RewardCreate.Field()
    create_news = NewsCreate.Field()
    create_event = EventCreate.Field()
    create_post = PostCreate.Field()
    create_activity = ActivityCreate.Field()
    create_comment = CommentCreate.Field()
    create_message_direct = MessageDirectCreate.Field()
    create_message_channel = MessageChannelCreate.Field()
    create_follow = FollowCreate.Field()
    create_like = LikeCreate.Field()
    create_bookmark = BookmarkCreate.Field()
    create_RSVP = RsvpCreate.Field()
    create_subscription = SubscriptionCreate.Field()

    update_organization = OrganizationUpdate.Field()
    update_person = PersonUpdate.Field()
    update_bot = BotUpdate.Field()
    update_news = NewsUpdate.Field()
    update_event = EventUpdate.Field()
    update_activity = ActivityUpdate.Field()

    delete_follow = FollowDelete.Field()
    delete_like = LikeDelete.Field()
    delete_bookmark = BookmarkDelete.Field()
    delete_RSVP = RsvpDelete.Field()
