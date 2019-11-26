from django.db import models
from django.core.validators import MinLengthValidator
from model_utils.models import TimeStampedModel, SoftDeletableModel

from users.models import User

# TODO: best way to handle this? maybe in settings?
CAT_MAX_LEN = 10
TITLE_MAX_LEN = 50
TX_MAX_LEN = 160
DESC_MAX_LEN = 320


class Scoreable(models.Model):
    score = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class IbisUser(User, Scoreable):
    class Meta:
        verbose_name_plural = 'ibis user'

    following = models.ManyToManyField(
        'self',
        related_name='follower',
        symmetrical=False,
        blank=True,
    )
    avatar = models.TextField()

    def __str__(self):
        return '{}{}{}'.format(
            self.first_name,
            ' ' if self.first_name and self.last_name else '',
            self.last_name,
        )


class Valuable(models.Model):
    amount = models.PositiveIntegerField()

    class Meta:
        abstract = True


class Likeable(models.Model):
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_%(class)s',
        blank=True,
    )

    class Meta:
        abstract = True


class Bookmarkable(models.Model):
    bookmark = models.ManyToManyField(
        IbisUser,
        related_name='bookmark_for_%(class)s',
        blank=True,
    )

    class Meta:
        abstract = True


class Rsvpable(models.Model):
    rsvp = models.ManyToManyField(
        IbisUser,
        related_name='rsvp_for_%(class)s',
        blank=True,
    )

    class Meta:
        abstract = True


class NonprofitCategory(models.Model):
    class Meta:
        verbose_name_plural = 'nonprofit categories'

    title = models.CharField(max_length=TITLE_MAX_LEN, unique=True)
    description = models.CharField(
        max_length=DESC_MAX_LEN,
        validators=[MinLengthValidator(1)],
    )

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Person(IbisUser):
    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "People"

    PUBLIC = 'PC'
    FOLLOWING = 'FL'
    PRIVATE = 'PR'

    VISIBILITY_CHOICES = (
        (PUBLIC, 'Public'),
        (FOLLOWING, 'Following Only'),
        (PRIVATE, 'Me Only'),
    )

    transaction_to = models.ManyToManyField(
        IbisUser,
        related_name='transaction_from',
        through='Transaction',
        symmetrical=False,
    )

    visibility_follow = models.CharField(
        max_length=2,
        choices=VISIBILITY_CHOICES,
        default=PUBLIC,
    )

    visibility_donation = models.CharField(
        max_length=2,
        choices=VISIBILITY_CHOICES,
        default=PUBLIC,
    )

    visibility_transaction = models.CharField(
        max_length=2,
        choices=VISIBILITY_CHOICES,
        default=PUBLIC,
    )

    notify_email_follow = models.BooleanField(default=True)
    notify_email_transaction = models.BooleanField(default=True)
    notify_email_like = models.BooleanField(default=False)


class Nonprofit(IbisUser, TimeStampedModel, SoftDeletableModel):
    class Meta:
        verbose_name = "Nonprofit"

    title = models.CharField(max_length=TITLE_MAX_LEN, unique=True)
    category = models.ForeignKey(
        NonprofitCategory,
        on_delete=models.CASCADE,
    )
    description = models.TextField()
    link = models.TextField()

    donation_to = models.ManyToManyField(
        IbisUser,
        related_name='donation_from',
        through='Donation',
        symmetrical=False,
    )

    def __str__(self):
        return self.title


class Entry(TimeStampedModel, SoftDeletableModel):
    class Meta:
        verbose_name = "Entry"
        verbose_name_plural = "Entries"

    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    description = models.TextField()


class Deposit(Valuable):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    payment_id = models.TextField(unique=True)


class Withdrawal(Valuable):
    user = models.ForeignKey(
        Nonprofit,
        on_delete=models.CASCADE,
    )


class Donation(Entry, Valuable, Likeable, Scoreable):
    target = models.ForeignKey(
        Nonprofit,
        on_delete=models.CASCADE,
    )


class Transaction(Entry, Valuable, Likeable, Scoreable):
    target = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
    )


class News(Entry, Likeable, Bookmarkable, Scoreable):
    class Meta:
        verbose_name_plural = 'news'

    title = models.CharField(max_length=TITLE_MAX_LEN)
    link = models.TextField()
    image = models.TextField()
    body = models.TextField()

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Event(Entry, Likeable, Bookmarkable, Rsvpable, Scoreable):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    link = models.TextField()
    image = models.TextField()
    date = models.DateTimeField()
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


# Votable must be concrete b/c is must be explicyt referenced by Vote
class Votable(Entry):
    vote = models.ManyToManyField(
        IbisUser,
        through='Vote',
        blank=True,
    )


class Post(Votable, Likeable, Bookmarkable, Scoreable):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    body = models.TextField()


class Comment(Votable, Likeable, Scoreable):
    parent = models.ForeignKey(
        Entry,
        related_name='parent_of',
        on_delete=models.CASCADE,
    )


class Vote(models.Model):
    user = models.ForeignKey(
        IbisUser,
        related_name='vote_for_%(class)s',
        on_delete=models.CASCADE,
    )
    target = models.ForeignKey(
        Votable,
        related_name='vote_from',
        on_delete=models.CASCADE,
    )
    is_upvote = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'target')
