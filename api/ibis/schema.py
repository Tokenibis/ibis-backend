import django_filters
import graphene

from django.db.models import Exists, OuterRef
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

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

    class Meta:
        model = models.IbisUser
        fields = ['is_donation']

    def filter_is_donation(self, queryset, name, value):
        queryset = queryset.annotate(
            is_donation=Exists(
                models.Nonprofit.objects.filter(
                    user_id=OuterRef('target_id')))).filter(is_donation=value)
        return queryset


class TransferNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.Transfer
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, info):
        return self.like.count()


class IbisUserFilter(django_filters.FilterSet):
    is_nonprofit = django_filters.BooleanFilter(method='filter_is_nonprofit')

    class Meta:
        model = models.IbisUser
        fields = ['is_nonprofit']

    def filter_is_nonprofit(self, queryset, name, value):
        queryset = queryset.annotate(
            is_nonprofit=Exists(
                models.Nonprofit.objects.filter(
                    user_id=OuterRef('user_id')))).filter(is_nonprofit=value)
        return queryset


class IbisUserNode(users.schema.UserNode):
    username = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    last_login = graphene.DateTime()
    date_joined = graphene.DateTime()

    following_count = graphene.Int()
    follower_count = graphene.Int()
    transfer_to = DjangoFilterConnectionField(TransferNode)
    transfer_from = DjangoFilterConnectionField(TransferNode)
    balance = graphene.Int()

    class Meta:
        model = models.IbisUser
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_username(self, info):
        return self.user.username

    def resolve_first_name(self, info):
        return self.user.first_name

    def resolve_last_name(self, info):
        return self.user.last_name

    def resolve_last_login(self, info):
        return self.user.last_login

    def resolve_date_joined(self, info):
        return self.user.date_joined

    def resolve_following_count(self, info):
        return self.following.count()

    def resolve_follower_count(self, info):
        return self.follower.count()

    def resolve_transfer_to(self, info):
        return models.Transfer.objects.filter(user=self)

    def resolve_transfer_from(self, info):
        return models.Transfer.objects.filter(target=self)

    def resolve_balance(self, info):
        ex_in = sum(
            [ex.amount for ex in self.exchange_set.all() if ex.is_withdrawal])
        ex_out = sum([
            ex.amount for ex in self.exchange_set.all() if not ex.is_withdrawal
        ])
        tx_in = sum(
            [tx.amount for tx in models.Transfer.objects.filter(target=self)])
        tx_out = sum(
            [tx.amount for tx in models.Transfer.objects.filter(user=self)])
        return (ex_in - ex_out) + (tx_in - tx_out)


class NewsNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.News
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, info):
        return self.like.count()


class EventNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.Event
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, info):
        return self.like.count()


class CommentNode(PostNode):
    upvote_count = graphene.Int()
    downvote_count = graphene.Int()

    class Meta:
        model = models.Comment
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_upvote_count(self, info):
        return self.vote.filter(usercommentvote__is_upvote=True).count()

    def resolve_downvote_count(self, info):
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
    all_news = DjangoFilterConnectionField(NewsNode)
    all_events = DjangoFilterConnectionField(EventNode)
    all_comments = DjangoFilterConnectionField(CommentNode)
