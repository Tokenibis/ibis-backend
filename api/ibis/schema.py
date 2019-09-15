import django_filters
import graphene

from django.db.models import Exists, OuterRef, Q, Count, Value
from django.db.models.functions import Concat
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id

import ibis.models as models
import users.schema


class NonprofitCategoryNode(DjangoObjectType):
    class Meta:
        model = models.NonprofitCategory
        filter_fields = []
        interfaces = (relay.Node, )


class NonprofitCategoryCreate(Mutation):
    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String(required=True)

    nonprofitCategory = graphene.Field(NonprofitCategoryNode)

    def mutate(self, info, title, description):
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
        try:
            models.NonprofitCategory.objects.get(
                pk=from_global_id(id)[1]).delete()
            return NonprofitCategoryDelete(status=True)
        except models.NonprofitCategory.DoesNotExist:
            return NonprofitCategoryDelete(status=False)


class NonprofitNode(DjangoObjectType):
    class Meta:
        model = models.Nonprofit
        filter_fields = []
        interfaces = (relay.Node, )


class ExchangeNode(DjangoObjectType):
    class Meta:
        model = models.Exchange
        filter_fields = []
        interfaces = (relay.Node, )


class PostNode(DjangoObjectType):
    class Meta:
        model = models.Post
        filter_fields = []
        interfaces = (relay.Node, )


class TransferFilter(django_filters.FilterSet):
    is_donation = django_filters.BooleanFilter(method='filter_is_donation')
    by_user = django_filters.CharFilter(method='filter_by_user')
    by_following = django_filters.CharFilter(method='filter_by_following')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.Transfer
        fields = ['is_donation', 'by_following']

    def filter_is_donation(self, qs, name, value):
        return qs.annotate(
            is_donation=Exists(
                models.Nonprofit.objects.filter(
                    user_id=OuterRef('target_id')))).filter(is_donation=value)

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


class TransferNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.Transfer
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, *args, **kwargs):
        return self.like.count()


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
                id=from_global_id(value)[1]).bookmark_for.all())

    def filter_by_following(self, qs, name, value):
        return qs.filter(
            user_id__in=models.IbisUser.objects.get(
                id=int(from_global_id(value)[1])).following.all())

    def filter_search(self, qs, name, value):
        return qs.annotate(
            user_name=Concat('user__first_name', Value(' '), 'user__last_name')
        ).filter(
            Q(user_name__icontains=value) | Q(user__username__icontains=value)
            | Q(title__icontains=value) | Q(description__icontains=value))


class NewsNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.News
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, *args, **kwargs):
        return self.like.count()


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
    rsvp_by = django_filters.CharFilter(method='filter_rsvp_by')
    by_following = django_filters.CharFilter(method='filter_by_following')
    begin_date = django_filters.CharFilter(method='filter_begin_date')
    end_date = django_filters.CharFilter(method='filter_end_date')
    order_by = EventOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.Event
        fields = ['by_following']

    def filter_by_user(self, qs, name, value):
        return qs.filter(user_id=from_global_id(value)[1])

    def filter_rsvp_by(self, qs, name, value):
        return qs.filter(
            id__in=models.IbisUser.objects.get(
                id=from_global_id(value)[1]).rsvp_for.all())

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
            user_name=Concat('user__first_name', Value(' '), 'user__last_name')
        ).filter(
            Q(user_name__icontains=value) | Q(user__username__icontains=value)
            | Q(title__icontains=value) | Q(description__icontains=value))


class EventNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.Event
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, *args, **kwargs):
        return self.like.count()


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
    is_nonprofit = django_filters.BooleanFilter(method='filter_is_nonprofit')
    followed_by = django_filters.CharFilter(method='filter_followed_by')
    follower_of = django_filters.CharFilter(method='filter_follower_of')
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
        fields = ['is_nonprofit']

    def filter_is_nonprofit(self, qs, name, value):
        return qs.annotate(
            is_nonprofit=Exists(
                models.Nonprofit.objects.filter(
                    user_id=OuterRef('id')))).filter(is_nonprofit=value)

    def filter_followed_by(self, qs, name, value):
        return qs.filter(
            id__in=models.IbisUser.objects.get(
                id=from_global_id(value)[1]).following.all())

    def filter_follower_of(self, qs, name, value):
        return qs.filter(
            id__in=models.IbisUser.objects.get(
                id=from_global_id(value)[1]).follower.all())

    def filter_search(self, qs, name, value):
        return qs.annotate(
            name=Concat('first_name', Value(' '), 'last_name')).filter(
                Q(name__icontains=value) | Q(username__icontains=value))


class IbisUserNode(users.schema.UserNode):
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
    balance = graphene.Int()

    transfer_to = DjangoFilterConnectionField(
        TransferNode,
        filterset_class=TransferFilter,
    )
    transfer_from = DjangoFilterConnectionField(
        TransferNode,
        filterset_class=TransferFilter,
    )
    transfer_set = DjangoFilterConnectionField(
        TransferNode,
        filterset_class=TransferFilter,
    )

    bookmark_for = DjangoFilterConnectionField(
        NewsNode,
        filterset_class=NewsFilter,
    )

    rsvp_for = DjangoFilterConnectionField(
        EventNode,
        filterset_class=EventFilter,
    )

    class Meta:
        model = models.IbisUser
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_following_count(self, *args, **kwargs):
        return self.following.count()

    def resolve_follower_count(self, *args, **kwargs):
        return self.follower.count()

    def resolve_balance(self, *args, **kwargs):
        exchange = sum([ex.amount for ex in self.exchange_set.all()])
        transfer_in = sum(
            [tx.amount for tx in models.Transfer.objects.filter(target=self)])
        transfer_out = sum(
            [tx.amount for tx in models.Transfer.objects.filter(user=self)])
        return (exchange) + (transfer_in - transfer_out)

    def resolve_transfer_to(self, *args, **kwargs):
        return models.Transfer.objects.filter(user=self)

    def resolve_transfer_from(self, *args, **kwargs):
        return models.Transfer.objects.filter(target=self)

    def resolve_transfer_set(self, *args, **kwargs):
        return models.Transfer.objects.filter(Q(user=self) | Q(target=self))

    def resolve_news_set(self, *args, **kwargs):
        return models.News.objects.filter(user=self)

    def resolve_event_set(self, *args, **kwargs):
        return models.Event.objects.filter(user=self)


class CommentNode(PostNode):
    upvote_count = graphene.Int()
    downvote_count = graphene.Int()

    class Meta:
        model = models.Comment
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_upvote_count(self, *args, **kwargs):
        return self.vote.filter(usercommentvote__is_upvote=True).count()

    def resolve_downvote_count(self, *args, **kwargs):
        return self.vote.filter(usercommentvote__is_upvote=False).count()


class Query(object):

    nonprofit_category = relay.Node.Field(NonprofitCategoryNode)
    ibis_user = relay.Node.Field(IbisUserNode)
    nonprofit = relay.Node.Field(NonprofitNode)
    exchange = relay.Node.Field(ExchangeNode)
    transfer = relay.Node.Field(TransferNode)
    news = relay.Node.Field(NewsNode)
    event = relay.Node.Field(EventNode)
    comment = relay.Node.Field(CommentNode)

    all_nonprofit_categories = DjangoFilterConnectionField(
        NonprofitCategoryNode)
    all_ibis_users = DjangoFilterConnectionField(
        IbisUserNode,
        filterset_class=IbisUserFilter,
    )
    all_nonprofits = DjangoFilterConnectionField(NonprofitNode)
    all_exchanges = DjangoFilterConnectionField(ExchangeNode)
    all_transfers = DjangoFilterConnectionField(
        TransferNode,
        filterset_class=TransferFilter,
    )
    all_news = DjangoFilterConnectionField(
        NewsNode,
        filterset_class=NewsFilter,
    )
    all_events = DjangoFilterConnectionField(
        EventNode,
        filterset_class=EventFilter,
    )
    all_comments = DjangoFilterConnectionField(CommentNode)


class Mutation(graphene.ObjectType):
    create_nonprofit_category = NonprofitCategoryCreate.Field()
    update_nonprofit_category = NonprofitCategoryUpdate.Field()
    delete_nonprofit_category = NonprofitCategoryDelete.Field()
