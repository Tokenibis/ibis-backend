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
    following = models.ManyToManyField(
        'self',
        related_name='follower',
        symmetrical=False,
        blank=True,
    )
    transaction_to = models.ManyToManyField(
        'self',
        related_name='transaction_from',
        through='Transaction',
        symmetrical=False,
    )

    def __str__(self):
        return '{} ({})'.format(self.user.username, self.user.id)


class NonprofitCategory(models.Model):
    class Meta:
        verbose_name_plural = 'nonprofit categories'

    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class PrivacyPolicy(models.Model):
    class Meta:
        verbose_name_plural = 'privacy policies'

    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class NotificationReason(models.Model):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Settings(models.Model):
    class Meta:
        verbose_name_plural = 'settings'

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
        blank=True,
    )
    push_notifications = models.ManyToManyField(
        NotificationReason,
        related_name='push_policy_of',
        blank=True,
    )
    email_notifications = models.ManyToManyField(
        NotificationReason,
        related_name='email_policy_of',
        blank=True,
    )

    def __str__(self):
        return 'settings {} ({})'.format(
            self.user.user.username,
            self.user.user.id,
        )


class Nonprofit(TimeStampedModel, SoftDeletableModel):
    user = models.OneToOneField(
        IbisUser,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    title = models.CharField(max_length=TITLE_MAX_LEN)
    category = models.ManyToManyField(NonprofitCategory)
    description = models.TextField()

    def __str__(self):
        return '{} ({})'.format(self.title, self.user.user.id)


class Exchange(TimeStampedModel):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    is_withdrawal = models.BooleanField()
    amount = models.PositiveIntegerField()

    def __str__(self):
        return '{} {} ({})'.format(
            'withdrawal' if self.is_withdrawal else 'deposit',
            self.user.user.username,
            self.id,
        )


class Post(TimeStampedModel, SoftDeletableModel):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    description = models.TextField()


class Transaction(Post):
    target = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField()
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_transaction',
        blank=True,
    )


class Article(Post):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    content = models.FileField()
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_article',
        blank=True,
    )

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Event(Post):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    link = models.TextField()
    rsvp = models.ManyToManyField(
        IbisUser,
        related_name='rsvp_for',
        blank=True,
    )
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_event',
        blank=True,
    )

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Comment(Post):
    parent = models.ForeignKey(
        Post,
        related_name='parent_of',
        on_delete=models.CASCADE,
    )
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
