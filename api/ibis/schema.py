import graphene

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


class TransactionNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.Transaction
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, info):
        return self.like.count()


class IbisUserNode(users.schema.UserNode):
    username = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    last_login = graphene.DateTime()
    date_joined = graphene.DateTime()

    followers = graphene.List(lambda: IbisUserNode)
    transaction_to = graphene.List(TransactionNode)
    transaction_from = graphene.List(TransactionNode)
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

    def resolve_follower(self, info):
        return self.follower_set.all()

    def resolve_transaction_to(self, info):
        return models.Transaction.objects.filter(user=self)

    def resolve_transaction_from(self, info):
        return models.Transaction.objects.filter(target=self)

    def resolve_balance(self, info):
        ex_in = sum([
            ex.amount for ex in self.exchange_set.all() if ex.is_withdrawal
        ])
        ex_out = sum([
            ex.amount for ex in self.exchange_set.all() if not ex.is_withdrawal
        ])
        tx_in = sum([
            tx.amount for tx in models.Transaction.objects.filter(target=self)
        ])
        tx_out = sum([
            tx.amount for tx in models.Transaction.objects.filter(user=self)
        ])
        return (ex_in - ex_out) + (tx_in - tx_out)


class ArticleNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.Article
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
    transaction = relay.Node.Field(TransactionNode)
    article = relay.Node.Field(ArticleNode)
    event = relay.Node.Field(EventNode)
    comment = relay.Node.Field(CommentNode)

    all_ibis_users = DjangoFilterConnectionField(IbisUserNode)
    all_nonprofits = DjangoFilterConnectionField(NonprofitNode)
    all_exchanges = DjangoFilterConnectionField(ExchangeNode)
    all_transactions = DjangoFilterConnectionField(TransactionNode)
    all_articles = DjangoFilterConnectionField(ArticleNode)
    all_events = DjangoFilterConnectionField(EventNode)
    all_comments = DjangoFilterConnectionField(CommentNode)
