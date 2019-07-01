import django_filters
import graphene

from django.db.models import Exists, OuterRef, Q, Count
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id

import ibis.models as models
import users.schema


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
    by_following = django_filters.CharFilter(method='filter_by_following')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))

    class Meta:
        model = models.Transfer
        fields = ['is_donation', 'by_following']

    def filter_is_donation(self, queryset, name, value):
        queryset = queryset.annotate(
            is_donation=Exists(
                models.Nonprofit.objects.filter(
                    user_id=OuterRef('target_id')))).filter(is_donation=value)
        return queryset

    def filter_by_following(self, queryset, name, value):
        queryset = queryset.filter(
            Q(
                target_id__in=models.IbisUser.objects.get(
                    id=int(from_global_id(value)[1])).following.all()) | Q(
                        user_id__in=models.IbisUser.objects.get(
                            id=int(from_global_id(value)[1])).following.all()))
        return queryset


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
    by_following = django_filters.CharFilter(method='filter_by_following')
    order_by = NewsOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))

    class Meta:
        model = models.News
        fields = ['by_following']

    def filter_by_following(self, queryset, name, value):
        queryset = queryset.filter(
            user_id__in=models.IbisUser.objects.get(
                id=int(from_global_id(value)[1])).following.all())
        return queryset


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
    by_following = django_filters.CharFilter(method='filter_by_following')
    order_by = EventOrderingFilter(
        fields=(
            ('score', 'score'),
            ('created', 'created'),
            ('like_count', 'like_count'),
        ))

    class Meta:
        model = models.Event
        fields = ['by_following']

    def filter_by_following(self, queryset, name, value):
        queryset = queryset.filter(
            user_id__in=models.IbisUser.objects.get(
                id=int(from_global_id(value)[1])).following.all())
        return queryset


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
    order_by = IbisUserOrderingFilter(
        fields=(
            ('score', 'score'),
            ('date_joined', 'date_joined'),
            ('follower_count', 'follower_count'),
            ('first_name', 'first_name'),
            ('last_name', 'last_name'),
        ))

    class Meta:
        model = models.IbisUser
        fields = ['is_nonprofit']

    def filter_is_nonprofit(self, queryset, name, value):
        queryset = queryset.annotate(
            is_nonprofit=Exists(
                models.Nonprofit.objects.filter(
                    user_id=OuterRef('id')))).filter(is_nonprofit=value)
        return queryset


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

    ibis_user = relay.Node.Field(IbisUserNode)
    nonprofit = relay.Node.Field(NonprofitNode)
    exchange = relay.Node.Field(ExchangeNode)
    transfer = relay.Node.Field(TransferNode)
    news = relay.Node.Field(NewsNode)
    event = relay.Node.Field(EventNode)
    comment = relay.Node.Field(CommentNode)

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
