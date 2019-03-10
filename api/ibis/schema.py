import graphene

from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

import ibis.models as models


class NonprofitNode(DjangoObjectType):
    class Meta:
        model = models.Nonprofit
        filter_fields = ['category', 'description']
        interfaces = (relay.Node, )


class ExchangeNode(DjangoObjectType):
    class Meta:
        model = models.Exchange
        filter_fields = []
        interfaces = (relay.Node, )


class PostNode(DjangoObjectType):
    upvote_count = graphene.Int()

    class Meta:
        model = models.Post
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_upvote_count(self, info):
        return self.upvote.count()


class TransactionNode(PostNode):
    class Meta:
        model = models.Transaction
        filter_fields = []
        interfaces = (relay.Node, )


class ArticleNode(PostNode):
    class Meta:
        model = models.Article
        filter_fields = []
        interfaces = (relay.Node, )


class EventNode(PostNode):
    class Meta:
        model = models.Event
        filter_fields = []
        interfaces = (relay.Node, )


class CommentNode(PostNode):
    downvote_count = graphene.Int()

    class Meta:
        model = models.Comment
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_downvote_count(self, info):
        return self.downvote.count()


class Query(object):

    nonprofit = relay.Node.Field(NonprofitNode)
    exchange = relay.Node.Field(ExchangeNode)
    transaction = relay.Node.Field(TransactionNode)
    article = relay.Node.Field(ArticleNode)
    event = relay.Node.Field(EventNode)
    comment = relay.Node.Field(CommentNode)

    all_nonprofits = DjangoFilterConnectionField(NonprofitNode)
    all_exchanges = DjangoFilterConnectionField(ExchangeNode)
    all_transactions = DjangoFilterConnectionField(TransactionNode)
    all_articles = DjangoFilterConnectionField(ArticleNode)
    all_events = DjangoFilterConnectionField(EventNode)
    all_comments = DjangoFilterConnectionField(CommentNode)
