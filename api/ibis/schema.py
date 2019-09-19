import django_filters
import graphene

from django.db.models import Q, Count, Value
from django.db.models.functions import Concat
from graphene import relay, Mutation
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id
import dateutil.parser

import ibis.models as models
from users.schema import UserNode

# --- Nonprofit Category ---------------------------------------------------- #


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


# --- Transaction Category -------------------------------------------------- #


class TransactionCategoryNode(DjangoObjectType):
    class Meta:
        model = models.TransactionCategory
        filter_fields = []
        interfaces = (relay.Node, )


class TransactionCategoryCreate(Mutation):
    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String(required=True)

    transactionCategory = graphene.Field(TransactionCategoryNode)

    def mutate(self, info, title, description):
        transactionCategory = models.TransactionCategory.objects.create(
            title=title,
            description=description,
        )
        transactionCategory.save()
        return TransactionCategoryCreate(
            transactionCategory=transactionCategory)


class TransactionCategoryUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String()
        description = graphene.String()

    transactionCategory = graphene.Field(TransactionCategoryNode)

    def mutate(self, info, id, title='', description=''):
        transactionCategory = models.TransactionCategory.objects.get(
            pk=from_global_id(id)[1])
        if title:
            transactionCategory.title = title
        if description:
            transactionCategory.description = description
        transactionCategory.save()
        return TransactionCategoryUpdate(
            transactionCategory=transactionCategory)


class TransactionCategoryDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.TransactionCategory.objects.get(
                pk=from_global_id(id)[1]).delete()
            return TransactionCategoryDelete(status=True)
        except models.TransactionCategory.DoesNotExist:
            return TransactionCategoryDelete(status=False)


# --- Deposit --------------------------------------------------------------- #


class DepositNode(DjangoObjectType):
    class Meta:
        model = models.Deposit
        filter_fields = []
        interfaces = (relay.Node, )


class DepositCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        amount = graphene.String(required=True)

    deposit = graphene.Field(DepositNode)

    def mutate(self, info, user, amount):
        deposit = models.Deposit.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            amount=amount,
        )
        deposit.save()
        return DepositCreate(deposit=deposit)


class DepositUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        amount = graphene.String()

    deposit = graphene.Field(DepositNode)

    def mutate(self, info, id, user=None, amount=''):
        deposit = models.Deposit.objects.get(pk=from_global_id(id)[1])
        if user:
            deposit.user = models.IbisUser.objects.get(
                pk=from_global_id(user)[1])
        if amount:
            deposit.amount = amount
        deposit.save()
        return DepositUpdate(deposit=deposit)


class DepositDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
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


class WithdrawalCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        amount = graphene.String(required=True)

    withdrawal = graphene.Field(WithdrawalNode)

    def mutate(self, info, user, amount):
        withdrawal = models.Withdrawal.objects.create(
            user=models.Nonprofit.objects.get(pk=from_global_id(user)[1]),
            amount=amount,
        )
        withdrawal.save()
        return WithdrawalCreate(withdrawal=withdrawal)


class WithdrawalUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        user = graphene.ID()
        amount = graphene.String()

    withdrawal = graphene.Field(WithdrawalNode)

    def mutate(self, info, id, user=None, amount=''):
        withdrawal = models.Withdrawal.objects.get(pk=from_global_id(id)[1])
        if user:
            withdrawal.user = models.Nonprofit.objects.get(
                pk=from_global_id(user)[1])
        if amount:
            withdrawal.amount = amount
        withdrawal.save()
        return WithdrawalUpdate(withdrawal=withdrawal)


class WithdrawalDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.Withdrawal.objects.get(pk=from_global_id(id)[1]).delete()
            return WithdrawalDelete(status=True)
        except models.Withdrawal.DoesNotExist:
            return WithdrawalDelete(status=False)


# --- Post ------------------------------------------------------------------ #


class PostNode(DjangoObjectType):
    class Meta:
        model = models.Post
        filter_fields = []
        interfaces = (relay.Node, )


# --- Transfer -------------------------------------------------------------- #


class TransferFilter(django_filters.FilterSet):
    by_user = django_filters.CharFilter(method='filter_by_user')
    by_following = django_filters.CharFilter(method='filter_by_following')
    order_by = django_filters.OrderingFilter(fields=(('created', 'created'), ))
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = models.Transfer
        fields = ['by_following']

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


# --- Donation -------------------------------------------------------------- #


class DonationNode(TransferNode):
    amount = graphene.Int()

    class Meta:
        model = models.Donation
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_amount(self, *args, **kwargs):
        return self.transfer.amount


class DonationCreate(Mutation):
    class Meta:
        model = models.Donation

    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        target = graphene.ID(required=True)
        amount = graphene.Int(required=True)

    donation = graphene.Field(DonationNode)

    def mutate(self, info, user, description, target, amount):
        donation = models.Donation.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            target=models.Nonprofit.objects.get(pk=from_global_id(target)[1]),
            amount=amount,
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
            category=None,
    ):
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
            donation.amount = amount
        if category:
            donation.category = models.TransactionCategory.objects.get(
                pk=from_global_id(category)[1])
        donation.save()
        return DonationUpdate(donation=donation)


class DonationDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.Donation.objects.get(pk=from_global_id(id)[1]).delete()
            return DonationDelete(status=True)
        except models.Donation.DoesNotExist:
            return DonationDelete(status=False)


# --- Transaction ----------------------------------------------------------- #


class TransactionNode(TransferNode):
    amount = graphene.Int()

    class Meta:
        model = models.Transaction
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_amount(self, *args, **kwargs):
        return self.transfer.amount


class TransactionCreate(Mutation):
    class Meta:
        model = models.Transaction

    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        target = graphene.ID(required=True)
        amount = graphene.Int(required=True)
        category = graphene.ID(required=True)

    transaction = graphene.Field(TransactionNode)

    def mutate(self, info, user, description, target, amount, category):
        transaction = models.Transaction.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            target=models.Person.objects.get(pk=from_global_id(target)[1]),
            amount=amount,
            category=models.TransactionCategory.objects.get(
                pk=from_global_id(category)[1]),
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
        category = graphene.ID()

    transaction = graphene.Field(TransactionNode)

    def mutate(
            self,
            info,
            id,
            user=None,
            description='',
            target=None,
            amount=0,
            category=None,
    ):
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
            transaction.amount = amount
        if category:
            transaction.category = models.TransactionCategory.objects.get(
                pk=from_global_id(category)[1])
        transaction.save()
        return TransactionUpdate(transaction=transaction)


class TransactionDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.Transaction.objects.get(pk=from_global_id(id)[1]).delete()
            return TransactionDelete(status=True)
        except models.Transaction.DoesNotExist:
            return TransactionDelete(status=False)


# --- News ------------------------------------------------------------------ #


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
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class NewsNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.News
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, *args, **kwargs):
        return self.like.count()


class NewsCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        title = graphene.String(required=True)
        link = graphene.String(required=True)
        content = graphene.String(required=True)
        score = graphene.Int(required=True)

    news = graphene.Field(NewsNode)

    def mutate(self, info, user, description, title, link, content, score):
        news = models.News.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            title=title,
            link=link,
            content=content,
            score=score,
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
        content = graphene.String()
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
            content='',
            score=0,
    ):
        news = models.News.objects.get(pk=from_global_id(id)[1])
        if user:
            news.user = models.IbisUser.objects.get(pk=from_global_id(user)[1])
        if description:
            news.description = description
        if title:
            news.title = title
        if link:
            news.link = link
        if content:
            news.content = content
        if score:
            news.score = score
        news.save()
        return NewsUpdate(news=news)


class NewsDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.News.objects.get(pk=from_global_id(id)[1]).delete()
            return NewsDelete(status=True)
        except models.News.DoesNotExist:
            return NewsDelete(status=False)


# --- Event ----------------------------------------------------------------- #


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
            user_name=Concat('user__first_name', Value(' '),
                             'user__last_name')).filter(
                                 Q(user_name__icontains=value)
                                 | Q(user__username__icontains=value)
                                 | Q(title__icontains=value))


class EventNode(PostNode):
    like_count = graphene.Int()

    class Meta:
        model = models.Event
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_like_count(self, *args, **kwargs):
        return self.like.count()


class EventCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        title = graphene.String(required=True)
        link = graphene.String(required=True)
        date = graphene.String(required=True)
        address = graphene.String(required=True)
        latitude = graphene.Float(required=True)
        longitude = graphene.Float(required=True)
        score = graphene.Int(required=True)

    event = graphene.Field(EventNode)

    def mutate(
            self,
            info,
            user,
            description,
            title,
            link,
            date,
            address,
            latitude,
            longitude,
            score,
    ):
        event = models.Event.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            title=title,
            link=link,
            date=dateutil.parser.parse(date),
            address=address,
            latitude=latitude,
            longitude=longitude,
            score=score,
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
        date = graphene.String()
        address = graphene.String()
        latitude = graphene.Float()
        longitude = graphene.Float()
        score = graphene.Int()

    event = graphene.Field(EventNode)

    def mutate(
            self,
            id,
            info,
            user=None,
            description='',
            title='',
            link='',
            date='',
            address='',
            latitude=None,
            longitude=None,
            score=0,
    ):
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
        if date:
            event.date = date
        if address:
            event.address = address
        if type(latitude) == float or type(latitude) == int:
            event.latitude = latitude
        if type(longitude) == float or type(longitude) == int:
            event.longitude = longitude
        event.save()
        return EventUpdate(event=event)


class EventDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.Event.objects.get(pk=from_global_id(id)[1]).delete()
            return EventDelete(status=True)
        except models.Event.DoesNotExist:
            return EventDelete(status=False)


# --- Ibis User ------------------------------------------------------------- #


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
        fields = []

    def filter_followed_by(self, qs, name, value):
        return qs.filter(
            id__in=self.Meta.model.objects.get(
                id=from_global_id(value)[1]).following.all())

    def filter_follower_of(self, qs, name, value):
        return qs.filter(
            id__in=self.Meta.model.objects.get(
                id=from_global_id(value)[1]).follower.all())

    def filter_search(self, qs, name, value):
        return qs.annotate(
            name=Concat('first_name', Value(' '), 'last_name')).filter(
                Q(name__icontains=value) | Q(username__icontains=value))


class IbisUserNode(UserNode):
    name = graphene.String()
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

    def resolve_name(self, *args, **kwargs):
        return str(self)

    def resolve_following_count(self, *args, **kwargs):
        return self.following.count()

    def resolve_follower_count(self, *args, **kwargs):
        return self.follower.count()

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


# --- Person ---------------------------------------------------------------- #


class PersonNode(IbisUserNode, UserNode):

    balance = graphene.Int()

    class Meta:
        model = models.Person
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_balance(self, *args, **kwargs):
        deposit = sum([ex.amount for ex in self.deposit_set.all()])
        transfer_in = sum([
            tx.transfer.amount
            for tx in models.Transaction.objects.filter(target=self)
        ])
        transfer_out = sum([
            tx.transfer.amount
            for tx in models.Transaction.objects.filter(user=self)
        ])
        return (deposit) + (transfer_in - transfer_out)


# --- Nonprofit ------------------------------------------------------------- #


class NonprofitNode(IbisUserNode):

    balance = graphene.Int()

    class Meta:
        model = models.Nonprofit
        filter_fields = []
        interfaces = (relay.Node, )

    def resolve_balance(self, *args, **kwargs):
        deposit = sum([ex.amount for ex in self.deposit_set.all()])
        withdrawal = sum([ex.amount for ex in self.withdrawal_set.all()])
        transfer_in = sum([
            tx.transfer.amount
            for tx in models.Transaction.objects.filter(target=self)
        ])
        transfer_out = sum([
            tx.transfer.amount
            for tx in models.Transaction.objects.filter(user=self)
        ])
        return (deposit - withdrawal) + (transfer_in - transfer_out)


class NonprofitCreate(Mutation):
    class Arguments:
        title = graphene.String(required=True)
        category = graphene.ID(required=True)
        description = graphene.String(required=True)
        link = graphene.String(required=True)

    nonprofit = graphene.Field(NonprofitNode)

    def mutate(self, info, user, title, category, description, link):
        nonprofit = models.Nonprofit.objects.create(
            title=title,
            description=description,
            link=link,
        )
        nonprofit.save()
        return NonprofitCreate(nonprofit=nonprofit)


class NonprofitUpdate(Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String()
        category = graphene.ID()
        description = graphene.String()
        link = graphene.String()

    nonprofit = graphene.Field(NonprofitNode)

    def mutate(self,
               info,
               id,
               title='',
               category=None,
               description='',
               link=''):
        nonprofit = models.Nonprofit.objects.get(pk=from_global_id(id)[1])
        if title:
            nonprofit.title = title
        if category:
            nonprofit.category = models.NonprofitCategories.objects.get(
                pk=from_global_id(category)[1])
        if description:
            nonprofit.description = description
        if link:
            nonprofit.link = link

        nonprofit.save()
        return NonprofitUpdate(nonprofit=nonprofit)


class NonprofitDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.Nonprofit.objects.get(pk=from_global_id(id)[1]).delete()
            return NonprofitDelete(status=True)
        except models.Nonprofit.DoesNotExist:
            return NonprofitDelete(status=False)


# --- Comment --------------------------------------------------------------- #


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


class CommentCreate(Mutation):
    class Arguments:
        user = graphene.ID(required=True)
        description = graphene.String(required=True)
        parent = graphene.ID(required=True)

    comment = graphene.Field(CommentNode)

    def mutate(self, info, user, description, parent):
        comment = models.Comment.objects.create(
            user=models.IbisUser.objects.get(pk=from_global_id(user)[1]),
            description=description,
            parent=models.Post.objects.get(pk=from_global_id(parent)[1]),
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
        comment = models.Comment.objects.get(pk=from_global_id(id)[1])
        if user:
            comment.user = models.IbisUser.objects.get(
                pk=from_global_id(user)[1])
        if description:
            comment.description = description
        if parent:
            comment.parent = models.Post.objects.get(
                pk=from_global_id(parent)[1])
        comment.save()
        return CommentUpdate(comment=comment)


class CommentDelete(Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    status = graphene.Boolean()

    def mutate(self, info, id):
        try:
            models.Comment.objects.get(pk=from_global_id(id)[1]).delete()
            return CommentDelete(status=True)
        except models.Comment.DoesNotExist:
            return CommentDelete(status=False)


class Query(object):

    nonprofit_category = relay.Node.Field(NonprofitCategoryNode)
    person = relay.Node.Field(PersonNode)
    nonprofit = relay.Node.Field(NonprofitNode)
    withdrawal = relay.Node.Field(WithdrawalNode)
    deposit = relay.Node.Field(DepositNode)
    donation = relay.Node.Field(DonationNode)
    transaction = relay.Node.Field(TransactionNode)
    news = relay.Node.Field(NewsNode)
    event = relay.Node.Field(EventNode)
    comment = relay.Node.Field(CommentNode)

    all_nonprofit_categories = DjangoFilterConnectionField(
        NonprofitCategoryNode)
    all_transfer_categories = DjangoFilterConnectionField(
        TransactionCategoryNode)
    all_people = DjangoFilterConnectionField(
        PersonNode,
        filterset_class=IbisUserFilter,
    )
    all_nonprofits = DjangoFilterConnectionField(
        NonprofitNode,
        filterset_class=IbisUserFilter,
    )
    all_deposits = DjangoFilterConnectionField(DepositNode)
    all_withdrawals = DjangoFilterConnectionField(WithdrawalNode)
    all_donations = DjangoFilterConnectionField(
        DonationNode,
        filterset_class=TransferFilter,
    )
    all_transactions = DjangoFilterConnectionField(
        TransactionNode,
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

    create_comment = CommentCreate.Field()
    update_comment = CommentUpdate.Field()
    delete_comment = CommentDelete.Field()
