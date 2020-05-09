import django_filters
import graphene

from django.db.models import Q, Count, Value
from django.db.models.functions import Concat
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from graphql import GraphQLError
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id
import dateutil.parser

import ibis.models as models
from users.schema import UserNode

# --- Filters --------------------------------------------------------------- #


class IbisUserOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super(IbisUserOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['follower_count', '-follower_count']:
                if v in value:
                    qs = qs.annotate(
                        follower_count=Count('follower')).order_by(v)
                    value.remove(v)

        return super(IbisUserOrderingFilter, self).filter(qs, value)


class IbisUserFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(method='filter_id')
    followed_by = django_filters.CharFilter(method='filter_followed_by')
    follower_of = django_filters.CharFilter(method='filter_follower_of')
    like_for = django_filters.CharFilter(method='filter_like_for')
    rsvp_for = django_filters.CharFilter(method='filter_rsvp_for')
    order_by = IbisUserOrderingFilter(
        fields=(
            ('score', 'score'),
            ('date_joined', 'date_joined'),
            ('follower_count', 'follower_count'),
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
        ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.IbisUser
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
        return qs.filter(id__in=entry_obj.like.all())

    def filter_rsvp_for(self, qs, name, value):
        entry_type, entry_id = from_global_id(value)
        submodels = {
            '{}Node'.format(x.__name__): x
            for x in models.Rsvpable.__subclasses__()
        }

        try:
            entry_obj = submodels[entry_type].objects.get(pk=entry_id)
        except (KeyError, ObjectDoesNotExist):
            raise KeyError('Object is not Rsvpable')

        return qs.filter(id__in=entry_obj.rsvp.all())

    def filter_search(self, qs, name, value):
        return qs.annotate(
            name=Concat('first_name', Value(' '), 'last_name')).filter(
                Q(name__icontains=value) | Q(username__icontains=value))


class DepositFilter(django_filters.FilterSet):
    by_user = django_filters.CharFilter(method='filter_by_user')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))

    def filter_by_user(self, qs, name, value):
        return qs.filter(Q(user_id=from_global_id(value)[1]))


class TransferFilter(django_filters.FilterSet):
    by_user = django_filters.CharFilter(method='filter_by_user')
    by_following = django_filters.CharFilter(method='filter_by_following')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))
    search = django_filters.CharFilter(method='filter_search')

    def filter_by_user(self, qs, name, value):
        return qs.filter(
            Q(user_id=from_global_id(value)[1])
            | Q(target_id=from_global_id(value)[1]))

    def filter_by_following(self, qs, name, value):
        return qs.filter(
            Q(
                target_id__in=models.IbisUser.objects.get(
                    id=int(from_global_id(value)[1])).following.all()) | Q(
                        user_id__in=models.IbisUser.objects.get(
                            id=int(from_global_id(value)[1])).following.all()))

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


class DonationFilter(TransferFilter):
    class Meta:
        model = models.Donation
        fields = []


class TransactionFilter(TransferFilter):
    class Meta:
        model = models.Transaction
        fields = []


class NewsOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super(NewsOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['like_count', '-like_count']:
                if v in value:
                    qs = qs.annotate(like_count=Count('like')).order_by(v)
                    value.remove(v)

        return super(NewsOrderingFilter, self).filter(qs, value)


class NewsFilter(django_filters.FilterSet):
    by_user = django_filters.CharFilter(method='filter_by_user')
    bookmark_by = django_filters.CharFilter(method='filter_bookmark_by')
    by_following = django_filters.CharFilter(method='filter_by_following')
    order_by = NewsOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.News
        fields = ['by_following']

    def filter_by_user(self, qs, name, value):
        return qs.filter(user_id=from_global_id(value)[1])

    def filter_bookmark_by(self, qs, name, value):
        return qs.filter(
            id__in=models.IbisUser.objects.get(
                id=from_global_id(value)[1]).bookmark_for_news.all())

    def filter_by_following(self, qs, name, value):
        return qs.filter(
            user_id__in=models.IbisUser.objects.get(
                id=int(from_global_id(value)[1])).following.all())

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class EventOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super(EventOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['like_count', '-like_count']:
                if v in value:
                    qs = qs.annotate(like_count=Count('like')).order_by(v)
                    value.remove(v)

        return super(EventOrderingFilter, self).filter(qs, value)


class EventFilter(django_filters.FilterSet):
    by_user = django_filters.CharFilter(method='filter_by_user')
    bookmark_by = django_filters.CharFilter(method='filter_bookmark_by')
    rsvp_by = django_filters.CharFilter(method='filter_rsvp_by')
    by_following = django_filters.CharFilter(method='filter_by_following')
    begin_date = django_filters.CharFilter(method='filter_begin_date')
    end_date = django_filters.CharFilter(method='filter_end_date')
    order_by = EventOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('date', 'date'),
            ('like_count', 'like_count'),
        ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.Event
        fields = ['by_following']

    def filter_by_user(self, qs, name, value):
        return qs.filter(user_id=from_global_id(value)[1])

    def filter_bookmark_by(self, qs, name, value):
        return qs.filter(
            id__in=models.IbisUser.objects.get(
                id=from_global_id(value)[1]).bookmark_for_event.all())

    def filter_rsvp_by(self, qs, name, value):
        return qs.filter(
            id__in=models.IbisUser.objects.get(
                id=from_global_id(value)[1]).rsvp_for_event.all())

    def filter_by_following(self, qs, name, value):
        return qs.filter(
            user_id__in=models.IbisUser.objects.get(
                id=int(from_global_id(value)[1])).following.all())

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


class PostOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super(PostOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['like_count', '-like_count']:
                if v in value:
                    qs = qs.annotate(like_count=Count('like')).order_by(v)
                    value.remove(v)

        return super(PostOrderingFilter, self).filter(qs, value)


class PostFilter(django_filters.FilterSet):
    by_user = django_filters.CharFilter(method='filter_by_user')
    by_following = django_filters.CharFilter(method='filter_by_following')
    bookmark_by = django_filters.CharFilter(method='filter_bookmark_by')
    search = django_filters.CharFilter(method='filter_search')

    order_by = PostOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))

    class Meta:
        model = models.Post
        fields = []

    def filter_by_user(self, qs, name, value):
        return qs.filter(user_id=from_global_id(value)[1])

    def filter_by_following(self, qs, name, value):
        return qs.filter(
            user_id__in=models.IbisUser.objects.get(
                id=int(from_global_id(value)[1])).following.all())

    def filter_bookmark_by(self, qs, name, value):
        return qs.filter(
            id__in=models.IbisUser.objects.get(
                id=from_global_id(value)[1]).bookmark_for_post.all())

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class CommentOrderingFilter(django_filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        super(CommentOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            for v in ['like_count', '-like_count']:
                if v in value:
                    qs = qs.annotate(like_count=Count('like')).order_by(v)
                    value.remove(v)

        return super(CommentOrderingFilter, self).filter(qs, value)


class CommentFilter(django_filters.FilterSet):
    by_user = django_filters.CharFilter(method='filter_by_user')
    by_following = django_filters.CharFilter(method='filter_by_following')
    has_parent = django_filters.CharFilter(method='filter_has_parent')
    search = django_filters.CharFilter(method='filter_search')

    order_by = PostOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))

    class Meta:
        model = models.Comment
        fields = []

    def filter_by_user(self, qs, name, value):
        return qs.filter(user_id=from_global_id(value)[1])

    def filter_by_following(self, qs, name, value):
        return qs.filter(
            user_id__in=models.IbisUser.objects.get(
                id=int(from_global_id(value)[1])).following.all())

    def filter_has_parent(self, qs, name, value):
        return qs.filter(parent_id=from_global_id(value)[1])

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value))


# --- Nonprofit Category ---------------------------------------------------- #


class NonprofitCategoryNode(DjangoObjectType):
    class Meta:
        model = models.NonprofitCategory
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')
        return queryset


class NonprofitCategoryCreate(Mutation):
    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String(required=True)
        score = graphene.String(required=True)

    nonprofitCategory = graphene.Field(NonprofitCategoryNode)

    def mutate(self, info, title, description):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        nonprofitCategory = models.NonprofitCategory.objects.create(
            title=title,
            description=description,
        )
        nonprofitCategory.save()
        return NonprofitCategoryCreate(nonprofitCategory=nonprofitCategory)


class NonprofitCategoryUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String()
        description = graphene.String()

    nonprofitCategory = graphene.Field(NonprofitCategoryNode)

    def mutate(self, info, id, title='', description=''):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        nonprofitCategory = models.NonprofitCategory.objects.get(
            pk=from_global_id(id)[1])
        if title:
            nonprofitCategory.title = title
        if description:
            nonprofitCategory.description = description
        nonprofitCategory.save()

        return NonprofitCategoryUpdate(nonprofitCategory=nonprofitCategory)


class NonprofitCategoryDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.NonprofitCategory.objects.get(
                pk=from_global_id(id)[1]).delete()
            return NonprofitCategoryDelete(status=True)
        except models.NonprofitCategory.DoesNotExist:
            return NonprofitCategoryDelete(status=False)


# --- Deposit Category ------------------------------------------------------ #


class DepositCategoryNode(DjangoObjectType):
    class Meta:
        model = models.DepositCategory
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')
        return queryset


class DepositCategoryCreate(Mutation):
    class Arguments:
        title = graphene.String(required=True)
        score = graphene.String(required=True)

    depositCategory = graphene.Field(DepositCategoryNode)

    def mutate(self, info, title):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        depositCategory = models.DepositCategory.objects.create(title=title, )
        depositCategory.save()
        return DepositCategoryCreate(depositCategory=depositCategory)


class DepositCategoryUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String()

    depositCategory = graphene.Field(DepositCategoryNode)

    def mutate(self, info, id, title=''):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        depositCategory = models.DepositCategory.objects.get(
            pk=from_global_id(id)[1])
        if title:
            depositCategory.title = title
        depositCategory.save()

        return DepositCategoryUpdate(depositCategory=depositCategory)


class DepositCategoryDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.DepositCategory.objects.get(
                pk=from_global_id(id)[1]).delete()
            return DepositCategoryDelete(status=True)
        except models.DepositCategory.DoesNotExist:
            return DepositCategoryDelete(status=False)


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


class DepositCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        amount = graphene.Int(required=True)
        payment_id = graphene.String(required=True)
        category = graphene.ID(required=True)

    deposit = graphene.Field(DepositNode)

    def mutate(self, info, user, amount, payment_id, category):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            assert amount > 0
            assert amount <= settings.MAX_EXCHANGE
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])

        deposit = models.Deposit.objects.create(
            user=user_obj,
            amount=amount,
            payment_id=payment_id,
            category=models.DepositCategory.objects.get(
                pk=from_global_id(category)[1]),
        )
        deposit.save()
        return DepositCreate(deposit=deposit)


class DepositUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        amount = graphene.Int()
        payment_id = graphene.String()
        category = graphene.ID()

    deposit = graphene.Field(DepositNode)

    def mutate(
            self,
            info,
            id,
            user=None,
            amount='',
            payment_id='',
            category=None,
    ):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            assert amount > 0
            assert amount <= settings.MAX_EXCHANGE
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        deposit = models.Deposit.objects.get(pk=from_global_id(id)[1])
        if user:
            deposit.user = models.IbisUser.objects.get(
                pk=from_global_id(user)[1])
        if amount:
            try:
                assert deposit.user.balance() - amount >= 0
            except AssertionError:
                raise GraphQLError('Balance would be below zero')
            deposit.amount = amount
        if payment_id:
            deposit.payment_id = payment_id
        if category:
            deposit.category = models.DepositCategory.objects.get(
                pk=from_global_id(category)[1])
        deposit.save()
        return DepositUpdate(deposit=deposit)


class DepositDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.Deposit.objects.get(pk=from_global_id(id)[1]).delete()
            return DepositDelete(status=True)
        except models.Deposit.DoesNotExist:
            return DepositDelete(status=False)


# --- Withdrawal --------------------------------------------------------------- #


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


class WithdrawalCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        amount = graphene.Int(required=True)

    withdrawal = graphene.Field(WithdrawalNode)

    def mutate(self, info, user, amount):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            assert amount > 0
            assert amount <= settings.MAX_EXCHANGE
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])

        try:
            assert hasattr(user_obj, 'nonprofit')
            assert user_obj.balance() - amount >= 0
        except AssertionError:
            raise GraphQLError('Balance would be below zero')

        withdrawal = models.Withdrawal.objects.create(
            user=user_obj.nonprofit,
            amount=amount,
        )
        withdrawal.save()
        return WithdrawalCreate(withdrawal=withdrawal)


class WithdrawalUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        amount = graphene.Int()

    withdrawal = graphene.Field(WithdrawalNode)

    def mutate(self, info, id, user=None, amount=''):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            assert amount > 0
            assert amount <= settings.MAX_EXCHANGE
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        withdrawal = models.Withdrawal.objects.get(pk=from_global_id(id)[1])
        if user:
            withdrawal.user = models.Nonprofit.objects.get(
                pk=from_global_id(user)[1])
        if amount:
            try:
                assert hasattr(withdrawal.user, 'nonprofit')
                assert withdrawal.user.balance() - amount >= 0
            except AssertionError:
                raise GraphQLError('Balance would be below zero')
            withdrawal.amount = amount
        withdrawal.save()
        return WithdrawalUpdate(withdrawal=withdrawal)


class WithdrawalDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.Withdrawal.objects.get(pk=from_global_id(id)[1]).delete()
            return WithdrawalDelete(status=True)
        except models.Withdrawal.DoesNotExist:
            return WithdrawalDelete(status=False)


# --- Entry ----------------------------------------------------------------- #


class EntryNode(DjangoObjectType):
    comments = DjangoFilterConnectionField(
        lambda: CommentNode,
        filterset_class=CommentFilter,
    )
    comment_count = graphene.Int()
    comment_count_recursive = graphene.Int()

    like = DjangoFilterConnectionField(
        lambda: IbisUserNode,
        filterset_class=IbisUserFilter,
    )
    like_count = graphene.Int()

    class Meta:
        model = models.Entry
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_comments(self, *args, **kwargs):
        return models.Comment.objects.filter(parent=self)

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

    def resolve_like(self, *args, **kwargs):
        return self.like

    def resolve_like_count(self, *args, **kwargs):
        return self.like.count()


# --- Donation -------------------------------------------------------------- #


class DonationNode(EntryNode):
    amount = graphene.Int()

    class Meta:
        model = models.Donation
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_amount(self, *args, **kwargs):
        return self.amount

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')

        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            Q(user__visibility_donation=models.IbisUser.PUBLIC)
            | (Q(user__visibility_donation=models.IbisUser.FOLLOWING)
               & Q(user__following__id__exact=info.context.user.id))
            | (Q(user_id=info.context.user.id)
               | Q(target_id=info.context.user.id))).distinct()


class DonationCreate(Mutation):
    class Meta:
        model = models.Donation

    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        target = graphene.ID(required=True)
        amount = graphene.Int(required=True)
        score = graphene.Int()

    donation = graphene.Field(DonationNode)

    def mutate(self, info, user, description, target, amount, score=0):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        try:
            assert len(description) > 0
            assert amount > 0
            assert amount <= settings.MAX_TRANSFER
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        target_obj = models.Nonprofit.objects.get(pk=from_global_id(target)[1])

        try:
            assert user_obj.balance() - amount >= 0
        except AssertionError:
            raise GraphQLError('Balance would be below zero')

        donation = models.Donation.objects.create(
            user=user_obj,
            description=description,
            target=target_obj,
            amount=amount,
            score=score,
        )
        donation.save()
        return DonationCreate(donation=donation)


class DonationUpdate(Mutation):
    class Meta:
        model = models.Donation

    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        description = graphene.String()
        target = graphene.ID()
        amount = graphene.Int()
        category = graphene.ID()

    donation = graphene.Field(DonationNode)

    def mutate(
            self,
            info,
            id,
            user=None,
            description='',
            target=None,
            amount=0,
    ):
        if not info.context.user.is_superuser:
            return

        try:
            assert len(description) > 0
            assert amount > 0
            assert amount <= settings.MAX_TRANSFER
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        donation = models.Donation.objects.get(pk=from_global_id(id)[1])
        if user:
            donation.user = models.IbisUser.objects.get(
                pk=from_global_id(user)[1])
        if description:
            donation.description = description
        if target:
            donation.target = models.Nonprofit.objects.get(
                pk=from_global_id(target)[1])
        if amount:
            try:
                assert donation.user.balance() - amount >= 0
            except AssertionError:
                raise GraphQLError('Balance would be below zero')
            donation.amount = amount
        donation.save()
        return DonationUpdate(donation=donation)


class DonationDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.Donation.objects.get(pk=from_global_id(id)[1]).delete()
            return DonationDelete(status=True)
        except models.Donation.DoesNotExist:
            return DonationDelete(status=False)


# --- Transaction ----------------------------------------------------------- #


class TransactionNode(EntryNode):
    amount = graphene.Int()

    class Meta:
        model = models.Transaction
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_amount(self, *args, **kwargs):
        return self.amount

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')

        if info.context.user.is_superuser:
            return queryset

        return queryset.filter(
            Q(user__visibility_transaction=models.IbisUser.PUBLIC)
            | (Q(user__visibility_transaction=models.IbisUser.FOLLOWING)
               & Q(user__following__id__exact=info.context.user.id))
            | (Q(user_id=info.context.user.id)
               | Q(target_id=info.context.user.id))).distinct()


class TransactionCreate(Mutation):
    class Meta:
        model = models.Transaction

    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        target = graphene.ID(required=True)
        amount = graphene.Int(required=True)
        score = graphene.Int()

    transaction = graphene.Field(TransactionNode)

    def mutate(
            self,
            info,
            user,
            description,
            target,
            amount,
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

        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        target_obj = models.Person.objects.get(pk=from_global_id(target)[1])

        try:
            assert user_obj.balance() - amount >= 0
        except AssertionError:
            raise GraphQLError('Balance would be below zero')

        transaction = models.Transaction.objects.create(
            user=user_obj,
            description=description,
            target=target_obj,
            amount=amount,
            score=score,
        )

        transaction.save()
        return TransactionCreate(transaction=transaction)


class TransactionUpdate(Mutation):
    class Meta:
        model = models.Transaction

    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        description = graphene.String()
        target = graphene.ID()
        amount = graphene.Int()

    transaction = graphene.Field(TransactionNode)

    def mutate(
            self,
            info,
            id,
            user=None,
            description='',
            target=None,
            amount=0,
    ):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            assert len(description) > 0
            assert amount > 0
            assert amount <= settings.MAX_TRANSFER
        except AssertionError:
            raise GraphQLError('Arguments do not satisfy constraints')

        transaction = models.Transaction.objects.get(pk=from_global_id(id)[1])
        if user:
            transaction.user = models.IbisUser.objects.get(
                pk=from_global_id(user)[1])
        if description:
            transaction.description = description
        if target:
            transaction.target = models.Person.objects.get(
                pk=from_global_id(target)[1])
        if amount:
            try:
                assert transaction.user.balance() - amount >= 0
            except AssertionError:
                raise GraphQLError('Balance would be below zero')
            transaction.amount = amount
        transaction.save()
        return TransactionUpdate(transaction=transaction)


class TransactionDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.Transaction.objects.get(pk=from_global_id(id)[1]).delete()
            return TransactionDelete(status=True)
        except models.Transaction.DoesNotExist:
            return TransactionDelete(status=False)


# --- News ------------------------------------------------------------------ #


class NewsNode(EntryNode):
    bookmark = DjangoFilterConnectionField(
        lambda: IbisUserNode,
        filterset_class=IbisUserFilter,
    )

    class Meta:
        model = models.News
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_bookmark(self, *args, **kwargs):
        return self.bookmark

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')
        return queryset


class NewsCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        title = graphene.String(required=True)
        image = graphene.String(required=True)
        score = graphene.Int()
        link = graphene.String()

    news = graphene.Field(NewsNode)

    def mutate(
            self,
            info,
            user,
            description,
            title,
            image,
            link='',
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Nonprofit.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        news = models.News.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            title=title,
            link=link,
            image=image,
            score=score,
        )
        if link:
            news.link = link
        news.save()
        return NewsCreate(news=news)


class NewsUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        description = graphene.String()
        title = graphene.String()
        link = graphene.String()
        image = graphene.String()
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
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Nonprofit.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        news = models.News.objects.get(pk=from_global_id(id)[1])
        if user:
            news.user = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        if description:
            news.description = description
        if title:
            news.title = title
        if link:
            news.link = link
        if image:
            news.image = image
        if score:
            news.score = score
        news.save()
        return NewsUpdate(news=news)


class NewsDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.News.objects.get(pk=from_global_id(id)[1]).delete()
            return NewsDelete(status=True)
        except models.News.DoesNotExist:
            return NewsDelete(status=False)


# --- Event ----------------------------------------------------------------- #


class EventNode(EntryNode):
    bookmark = DjangoFilterConnectionField(
        lambda: IbisUserNode,
        filterset_class=IbisUserFilter,
    )
    rsvp = DjangoFilterConnectionField(
        lambda: IbisUserNode,
        filterset_class=IbisUserFilter,
    )
    rsvp_count = graphene.Int()

    class Meta:
        model = models.Event
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_bookmark(self, *args, **kwargs):
        return self.bookmark

    def resolve_rsvp(self, *args, **kwargs):
        return self.rsvp

    def resolve_rsvp_count(self, *args, **kwargs):
        return self.rsvp.count()

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')
        return queryset


class EventCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        title = graphene.String(required=True)
        image = graphene.String(required=True)
        date = graphene.String(required=True)
        duration = graphene.Int(required=True)
        address = graphene.String(required=True)
        link = graphene.String()
        score = graphene.Int()

    event = graphene.Field(EventNode)

    def mutate(
            self,
            info,
            user,
            description,
            title,
            image,
            date,
            duration,
            address,
            link='',
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Nonprofit.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        event = models.Event.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            title=title,
            image=image,
            date=dateutil.parser.parse(date),
            duration=duration,
            address=address,
            score=score,
        )
        if link:
            event.link = link
        event.save()
        return EventCreate(event=event)


class EventUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        description = graphene.String()
        title = graphene.String()
        link = graphene.String()
        image = graphene.String()
        date = graphene.String()
        duration = graphene.Int()
        address = graphene.String()
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
            score=0,
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Nonprofit.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        event = models.Event.objects.get(pk=from_global_id(id)[1])
        if user:
            event.user = models.IbisUser.objects.get(
                pk=from_global_id(user)[1])
        if description:
            event.description = description
        if title:
            event.title = title
        if link:
            event.link = link
        if image:
            event.image = image
        if date:
            event.date = date
        if type(duration) == int:
            event.duration = duration
        if address:
            event.address = address
        event.save()
        return EventUpdate(event=event)


class EventDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.Event.objects.get(pk=from_global_id(id)[1]).delete()
            return EventDelete(status=True)
        except models.Event.DoesNotExist:
            return EventDelete(status=False)


# --- Ibis User ------------------------------------------------------------- #


class IbisUserNode(UserNode):
    name = graphene.String()
    balance = graphene.Int()
    following = DjangoFilterConnectionField(
        lambda: IbisUserNode,
        filterset_class=IbisUserFilter,
    )
    follower = DjangoFilterConnectionField(
        lambda: IbisUserNode,
        filterset_class=IbisUserFilter,
    )
    following_count = graphene.Int()
    follower_count = graphene.Int()
    following_count_person = graphene.Int()
    following_count_nonprofit = graphene.Int()
    follower_count_person = graphene.Int()
    follower_count_nonprofit = graphene.Int()

    donation_to_count = graphene.Int()
    transaction_to_count = graphene.Int()
    news_count = graphene.Int()
    event_count = graphene.Int()
    post_count = graphene.Int()
    event_rsvp_count = graphene.Int()

    class Meta:
        model = models.IbisUser
        exclude = ['email', 'password']
        filter_fields = []
        interfaces = (relay.Node, )

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

    def resolve_following_count_nonprofit(self, *args, **kwargs):
        return len(
            [x for x in self.following.all() if hasattr(x, 'nonprofit')])

    def resolve_follower_count_person(self, *args, **kwargs):
        return len([x for x in self.follower.all() if hasattr(x, 'person')])

    def resolve_follower_count_nonprofit(self, *args, **kwargs):
        return len([x for x in self.follower.all() if hasattr(x, 'nonprofit')])

    def resolve_donation_to_count(self, *args, **kwargs):
        return models.Donation.objects.filter(user__id=self.id).count()

    def resolve_transaction_to_count(self, *args, **kwargs):
        return models.Transaction.objects.filter(user__id=self.id).count()

    def resolve_news_count(self, *args, **kwargs):
        return models.News.objects.filter(user__id=self.id).count()

    def resolve_event_count(self, *args, **kwargs):
        return models.Event.objects.filter(user__id=self.id).count()

    def resolve_post_count(self, *args, **kwargs):
        return models.Post.objects.filter(user__id=self.id).count()

    def resolve_event_rsvp_count(self, *args, **kwargs):
        return self.rsvp_for_event.all().count()

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')
        return queryset


# --- Person ---------------------------------------------------------------- #


class PersonNode(IbisUserNode, UserNode):

    donated = graphene.Int()

    visibility_follow = graphene.String()
    visibility_donation = graphene.String()
    visibility_transaction = graphene.String()

    transaction_from_count = graphene.Int()

    class Meta:
        model = models.Person
        exclude = ['email', 'password']
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_donated(self, *args, **kwargs):
        return self.donated()

    def resolve_visibility_following(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser or info.context.user.id == self.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.visibility_following

    def resolve_visibility_donation(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser or info.context.user.id == self.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.visibility_donation

    def resolve_visibility_transaction(self, info, *args, **kwargs):
        if not (info.context.user.is_superuser or info.context.user.id == self.id):
            raise GraphQLError('You do not have sufficient permission')
        return self.visibility_transaction

    def resolve_transaction_from_count(self, *args, **kwargs):
        return models.Transaction.objects.filter(target__id=self.id).count()


class PersonCreate(Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        first_name = graphene.String(required=True)
        last_name = graphene.String(required=True)
        visibility_follow = graphene.String()
        visibility_donation = graphene.String()
        visibility_transaction = graphene.String()
        score = graphene.Int()

    person = graphene.Field(PersonNode)

    def mutate(
            self,
            info,
            username,
            email,
            first_name,
            last_name,
            visibility_follow=models.IbisUser.PUBLIC,
            visibility_donation=models.IbisUser.PUBLIC,
            visibility_transaction=models.IbisUser.PUBLIC,
            score=0,
    ):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        if visibility_follow:
            assert visibility_follow in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
        if visibility_donation:
            assert visibility_donation in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
        if visibility_transaction:
            assert visibility_transaction in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]

        person = models.Person.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            visibility_follow=visibility_follow,
            visibility_donation=visibility_donation,
            visibility_transaction=visibility_transaction,
            score=score,
        )
        person.save()
        return PersonCreate(person=person)


class PersonUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        username = graphene.String()
        email = graphene.String()
        first_name = graphene.String()
        last_name = graphene.String()
        visibility_follow = graphene.String()
        visibility_donation = graphene.String()
        visibility_transaction = graphene.String()
        score = graphene.Int()

    person = graphene.Field(PersonNode)

    def mutate(
            self,
            info,
            id,
            username='',
            email='',
            first_name='',
            last_name='',
            visibility_follow='',
            visibility_donation='',
            visibility_transaction='',
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
        if first_name:
            person.first_name = first_name
        if last_name:
            person.first_name = last_name
        if visibility_follow:
            assert visibility_follow in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
            person.visibility_follow = visibility_follow
        if visibility_donation:
            assert visibility_donation in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
            person.visibility_donation = visibility_donation
        if visibility_transaction:
            assert visibility_transaction in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
            person.visibility_transaction = visibility_transaction
        if type(score) == int:
            person.score = score
        person.save()
        return PersonUpdate(person=person)


class PersonDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.IbisUser.objects.get(pk=from_global_id(id)[1]).delete()
            return PersonDelete(status=True)
        except models.IbisUser.DoesNotExist:
            return PersonDelete(status=False)


# --- Nonprofit ------------------------------------------------------------- #


class NonprofitNode(IbisUserNode):

    fundraised = graphene.Int()

    donation_from_count = graphene.Int()

    class Meta:
        model = models.Nonprofit
        exclude = ['email', 'password']
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_fundraised(self, *args, **kwargs):
        return self.fundraised()

    def resolve_donation_from_count(self, *args, **kwargs):
        return models.Donation.objects.filter(target__id=self.id).count()


class NonprofitCreate(Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        category = graphene.ID(required=True)
        description = graphene.String(required=True)
        last_name = graphene.String(required=True)
        link = graphene.String(required=True)
        visibility_follow = graphene.String()
        visibility_donation = graphene.String()
        visibility_transaction = graphene.String()
        score = graphene.Int()

    nonprofit = graphene.Field(NonprofitNode)

    def mutate(
            self,
            info,
            username,
            email,
            category,
            description,
            last_name,
            link,
            visibility_follow=models.IbisUser.PUBLIC,
            visibility_donation=models.IbisUser.PUBLIC,
            visibility_transaction=models.IbisUser.PUBLIC,
            score=0,
    ):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        if visibility_follow:
            assert visibility_follow in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
        if visibility_donation:
            assert visibility_donation in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
        if visibility_transaction:
            assert visibility_transaction in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]

        nonprofit = models.Nonprofit.objects.create(
            username=username,
            email=email,
            first_name='',
            last_name=last_name,
            description=description,
            link=link,
            category=models.NonprofitCategory.objects.get(
                pk=from_global_id(category)[1]),
            score=score,
        )
        nonprofit.save()
        return NonprofitCreate(nonprofit=nonprofit)


class NonprofitUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        username = graphene.String()
        email = graphene.String()
        category = graphene.ID()
        description = graphene.String()
        last_name = graphene.String()
        link = graphene.String()
        visibility_follow = graphene.String()
        visibility_donation = graphene.String()
        visibility_transaction = graphene.String()
        score = graphene.Int()

    nonprofit = graphene.Field(NonprofitNode)

    def mutate(
            self,
            info,
            id,
            username='',
            email='',
            category=None,
            description='',
            last_name='',
            link='',
            visibility_follow='',
            visibility_donation='',
            visibility_transaction='',
            score=0,
    ):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(id)[1])):
            raise GraphQLError('You do not have sufficient permission')

        nonprofit = models.Nonprofit.objects.get(pk=from_global_id(id)[1])
        if username:
            nonprofit.username = username
        if email:
            nonprofit.email = email
        if last_name:
            nonprofit.last_name = last_name
        if category:
            nonprofit.category = models.NonprofitCategory.objects.get(
                pk=from_global_id(category)[1])
        if description:
            nonprofit.description = description
        if link:
            nonprofit.link = link
        if visibility_follow:
            assert visibility_follow in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
            nonprofit.visibility_follow = visibility_follow
        if visibility_donation:
            assert visibility_donation in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
            nonprofit.visibility_donation = visibility_donation
        if visibility_transaction:
            assert visibility_transaction in [
                models.IbisUser.PUBLIC, models.IbisUser.FOLLOWING,
                models.IbisUser.PRIVATE
            ]
            nonprofit.visibility_transaction = visibility_transaction
        if type(score) == int:
            nonprofit.score = score

        nonprofit.save()
        return NonprofitUpdate(nonprofit=nonprofit)


class NonprofitDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.IbisUser.objects.get(pk=from_global_id(id)[1]).delete()
            return NonprofitDelete(status=True)
        except models.IbisUser.DoesNotExist:
            return NonprofitDelete(status=False)


# --- Post ------------------------------------------------------------------ #


class PostNode(EntryNode):

    bookmark = DjangoFilterConnectionField(
        lambda: IbisUserNode,
        filterset_class=IbisUserFilter,
    )

    class Meta:
        model = models.Post
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_bookmark(self, *args, **kwargs):
        return self.bookmark

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')
        return queryset


class PostCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        title = graphene.String(required=True)
        description = graphene.String(required=True)

    post = graphene.Field(PostNode)

    def mutate(self, info, user, title, description):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Person.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        post = models.Post.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            title=title,
            description=description,
        )
        post.save()
        return PostCreate(post=post)


class PostUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        title = graphene.String()
        description = graphene.String()

    post = graphene.Field(PostNode)

    def mutate(
            self,
            info,
            user=None,
            title='',
            description='',
    ):
        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1]))
                and models.Person.objects.filter(
                    id=info.context.user.id).exists()):
            raise GraphQLError('You do not have sufficient permission')

        post = models.Post.objects.get(pk=from_global_id(id)[1])
        if user:
            post.user = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        if title:
            post.title = title
        if description:
            post.description = description
        post.save()
        return PostUpdate(post=post)


class PostDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.Post.objects.get(pk=from_global_id(id)[1]).delete()
            return PostDelete(status=True)
        except models.Post.DoesNotExist:
            return PostDelete(status=False)


# --- Comment --------------------------------------------------------------- #


class CommentNode(EntryNode):
    class Meta:
        model = models.Comment
        filter_fields = []
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        if not info.context.user.is_authenticated:
            raise GraphQLError('You are not  logged in')
        return queryset


class CommentCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        parent = graphene.ID(required=True)

    comment = graphene.Field(CommentNode)

    def mutate(self, info, user, description, parent):
        parent_obj = models.Entry.objects.get(pk=from_global_id(parent)[1])

        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1])
                 and hasattr(info.context.user, 'ibisuser')
                 and info.context.user.ibisuser.can_see(parent_obj))):
            raise GraphQLError('You do not have sufficient permission')

        comment = models.Comment.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            parent=parent_obj,
        )
        comment.save()
        return CommentCreate(comment=comment)


class CommentUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        description = graphene.String()
        parent = graphene.ID()

    comment = graphene.Field(CommentNode)

    def mutate(
            self,
            info,
            user=None,
            description='',
            parent=None,
    ):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        comment = models.Comment.objects.get(pk=from_global_id(id)[1])
        if user:
            comment.user = models.IbisUser.objects.get(
                pk=from_global_id(user)[1])
        if description:
            comment.description = description
        if parent:
            comment.parent = models.Entry.objects.get(
                pk=from_global_id(parent)[1])
        comment.save()
        return CommentUpdate(comment=comment)


class CommentDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        if not info.context.user.is_superuser:
            raise GraphQLError('You are not a staff member')

        try:
            models.Comment.objects.get(pk=from_global_id(id)[1]).delete()
            return CommentDelete(status=True)
        except models.Comment.DoesNotExist:
            return CommentDelete(status=False)


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

        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        target_obj = models.IbisUser.objects.get(pk=from_global_id(target)[1])
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
        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        entry_obj = models.Entry.objects.get(pk=from_global_id(target)[1])

        if not (info.context.user.is_superuser or
                (info.context.user.id == int(from_global_id(user)[1])
                 and hasattr(info.context.user, 'ibisuser')
                 and info.context.user.ibisuser.can_see(entry_obj))):
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


# --- Bookmarks ----------------------------------------------------------------- #


class BookmarkMutation(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        target = graphene.ID(required=True)

    state = graphene.Boolean()

    @classmethod
    def mutate(cls, info, operation, user, target):
        if not (info.context.user.is_superuser
                or info.context.user.id == int(from_global_id(user)[1])):
            raise GraphQLError('You do not have sufficient permission')

        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        entry_type, entry_id = from_global_id(target)

        submodels = {
            '{}Node'.format(x.__name__): x
            for x in models.Bookmarkable.__subclasses__()
        }

        try:
            entry_obj = submodels[entry_type].objects.get(pk=entry_id)
        except (KeyError, ObjectDoesNotExist):
            raise KeyError('Object is not bookmarkable')

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

        user_obj = models.IbisUser.objects.get(pk=from_global_id(user)[1])
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


# --------------------------------------------------------------------------- #


class Query(object):

    nonprofit_category = relay.Node.Field(NonprofitCategoryNode)
    deposit_category = relay.Node.Field(DepositCategoryNode)
    ibis_user = relay.Node.Field(IbisUserNode)
    person = relay.Node.Field(PersonNode)
    nonprofit = relay.Node.Field(NonprofitNode)
    withdrawal = relay.Node.Field(WithdrawalNode)
    deposit = relay.Node.Field(DepositNode)
    donation = relay.Node.Field(DonationNode)
    transaction = relay.Node.Field(TransactionNode)
    news = relay.Node.Field(NewsNode)
    event = relay.Node.Field(EventNode)
    post = relay.Node.Field(PostNode)
    comment = relay.Node.Field(CommentNode)

    all_nonprofit_categories = DjangoFilterConnectionField(
        NonprofitCategoryNode)
    all_deposit_categories = DjangoFilterConnectionField(DepositCategoryNode)
    all_ibis_users = DjangoFilterConnectionField(
        IbisUserNode,
        filterset_class=IbisUserFilter,
    )
    all_people = DjangoFilterConnectionField(
        PersonNode,
        filterset_class=IbisUserFilter,
    )
    all_nonprofits = DjangoFilterConnectionField(
        NonprofitNode,
        filterset_class=IbisUserFilter,
    )
    all_deposits = DjangoFilterConnectionField(
        DepositNode,
        filterset_class=DepositFilter,
    )
    all_withdrawals = DjangoFilterConnectionField(WithdrawalNode)
    all_donations = DjangoFilterConnectionField(
        DonationNode,
        filterset_class=DonationFilter,
    )
    all_transactions = DjangoFilterConnectionField(
        TransactionNode,
        filterset_class=TransactionFilter,
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
    all_comments = DjangoFilterConnectionField(
        CommentNode,
        filterset_class=CommentFilter,
    )


class Mutation(graphene.ObjectType):
    create_nonprofit_category = NonprofitCategoryCreate.Field()
    update_nonprofit_category = NonprofitCategoryUpdate.Field()
    delete_nonprofit_category = NonprofitCategoryDelete.Field()

    create_person = PersonCreate.Field()
    update_person = PersonUpdate.Field()
    delete_person = PersonDelete.Field()

    create_nonprofit = NonprofitCreate.Field()
    update_nonprofit = NonprofitUpdate.Field()
    delete_nonprofit = NonprofitDelete.Field()

    create_deposit = DepositCreate.Field()
    update_deposit = DepositUpdate.Field()
    delete_deposit = DepositDelete.Field()

    create_withdrawal = WithdrawalCreate.Field()
    update_withdrawal = WithdrawalUpdate.Field()
    delete_withdrawal = WithdrawalDelete.Field()

    create_donation = DonationCreate.Field()
    update_donation = DonationUpdate.Field()
    delete_donation = DonationDelete.Field()

    create_transaction = TransactionCreate.Field()
    update_transaction = TransactionUpdate.Field()
    delete_transaction = TransactionDelete.Field()

    create_news = NewsCreate.Field()
    update_news = NewsUpdate.Field()
    delete_news = NewsDelete.Field()

    create_event = EventCreate.Field()
    update_event = EventUpdate.Field()
    delete_event = EventDelete.Field()

    create_post = PostCreate.Field()
    update_post = PostUpdate.Field()
    delete_post = PostDelete.Field()

    create_comment = CommentCreate.Field()
    update_comment = CommentUpdate.Field()
    delete_comment = CommentDelete.Field()

    create_follow = FollowCreate.Field()
    delete_follow = FollowDelete.Field()

    create_like = LikeCreate.Field()
    delete_like = LikeDelete.Field()

    create_bookmark = BookmarkCreate.Field()
    delete_bookmark = BookmarkDelete.Field()

    create_RSVP = RsvpCreate.Field()
    delete_RSVP = RsvpDelete.Field()
