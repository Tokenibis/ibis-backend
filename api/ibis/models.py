from django.db import models
from model_utils.models import TimeStampedModel, SoftDeletableModel

from users.models import User

# TODO: best way to handle this? maybe in settings?
CAT_MAX_LEN = 10
TITLE_MAX_LEN = 50
TX_MAX_LEN = 160
DESC_MAX_LEN = 320


class IbisUser(models.Model):
    class Meta:
        verbose_name_plural = 'ibis user'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    transaction_to = models.ManyToManyField(
        'self',
        related_name='transaction_from',
        through='Transaction',
        symmetrical=False,
    )
    following = models.ManyToManyField(
        'self',
        related_name='follower',
        symmetrical=False,
    )


class NonprofitCategory(models.Model):
    class Meta:
        verbose_name_plural = 'nonprofit categories'

    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)


class PrivacyPolicy(models.Model):
    class Meta:
        verbose_name_plural = 'privacy policies'

    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)


class NotificationReason(models.Model):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)


class Settings(models.Model):
    user = models.OneToOneField(
        IbisUser,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    follow_privacy = models.ForeignKey(
        PrivacyPolicy,
        related_name='follow_privacy_of',
        on_delete=models.PROTECT,
    )
    transaction_privacy = models.ForeignKey(
        PrivacyPolicy,
        related_name='transaction_privacy_of',
        on_delete=models.PROTECT,
    )
    blocked_users = models.ManyToManyField(
        IbisUser,
        related_name='blocked_user_of',
    )
    push_notifications = models.ManyToManyField(
        NotificationReason,
        related_name='push_policy_of',
    )
    email_notifications = models.ManyToManyField(
        NotificationReason, related_name='email_policy_of')


class Nonprofit(TimeStampedModel, SoftDeletableModel):
    user = models.OneToOneField(
        IbisUser,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    category = models.ManyToManyField(NonprofitCategory)
    description = models.TextField()


class Exchange(TimeStampedModel):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    is_withdrawal = models.BooleanField()
    amount = models.PositiveIntegerField()


class Post(TimeStampedModel, SoftDeletableModel):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )


class Transaction(Post):
    target = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField()
    description = models.CharField(max_length=TX_MAX_LEN)
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_transaction',
    )


class Article(Post):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)
    content = models.FileField()
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_article',
    )


class Event(Post):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    link = models.TextField()
    description = models.CharField(max_length=DESC_MAX_LEN)
    rsvp = models.ManyToManyField(
        IbisUser,
        related_name='rsvp_for',
    )
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_event',
    )


class Comment(Post):
    parent = models.ForeignKey(
        Post,
        related_name='parent_of',
        on_delete=models.CASCADE,
    )
    content = models.TextField()
    vote = models.ManyToManyField(
        IbisUser,
        through='UserCommentVote',
    )


class UserCommentVote(models.Model):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
    )
    is_upvote = models.BooleanField(default=True)
