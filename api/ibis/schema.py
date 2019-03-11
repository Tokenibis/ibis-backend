import graphene

from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

import ibis.models as models


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


class IbisUserNode(DjangoObjectType):
    class Meta:
        model = models.IbisUser
        filter_fields = []
        interfaces = (relay.Node, )

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
