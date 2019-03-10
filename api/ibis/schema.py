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
    class Meta:
        model = models.Post
        filter_fields = []
        interfaces = (relay.Node, )


class TransactionNode(DjangoObjectType):
    class Meta:
        model = models.Transaction
        filter_fields = []
        interfaces = (relay.Node, )


class ArticleNode(DjangoObjectType):
    class Meta:
        model = models.Article
        filter_fields = []
        interfaces = (relay.Node, )


class EventNode(DjangoObjectType):
    class Meta:
        model = models.Event
        filter_fields = []
        interfaces = (relay.Node, )


class CommentNode(DjangoObjectType):
    class Meta:
        model = models.Comment
        filter_fields = []
        interfaces = (relay.Node, )


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
