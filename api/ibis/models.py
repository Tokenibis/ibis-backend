from django.db import models
from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.models import StatusModel, SoftDeletableModel
from profiles.models import Profile

# TODO: best way to handle this? maybe in settings?
CAT_MAX_LEN = 10
TITLE_MAX_LEN = 50
TX_MAX_LEN = 160
DESC_MAX_LEN = 320


class NonprofitCategory(models.Model):
    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)

    user = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        primary_key=True,
    )

class Nonprofit(TimeStampedModel, SoftDeletableModel, StatusModel):
    user = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    category = models.ManyToManyField(NonprofitCategory)
    description = models.TextField()

    STATUS = Choices('pending', 'approved')


class Follow(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    target = models.OneToOneField(
        Profile,
        related_name='follower',
        on_delete=models.CASCADE,
    )


class Exchange(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    is_deposit = models.BooleanField()
    amount = models.PositiveIntegerField()


class Post(TimeStampedModel, SoftDeletableModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    upvote = models.ManyToManyField(
        Profile,
        related_name='upvoted',
        through='UpvoteEvent')


class Transaction(StatusModel):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    target = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )

    amount = models.PositiveIntegerField()
    description = models.CharField(max_length=TX_MAX_LEN)

    STATUS = Choices('requested', 'completed')


class Article(StatusModel):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)
    content = models.FileField()

    STATUS = Choices('draft', 'published')


class Event(StatusModel):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    title = models.CharField(max_length=TITLE_MAX_LEN)
    link = models.TextField()
    description = models.CharField(max_length=DESC_MAX_LEN)
    rsvp = models.ManyToManyField(Profile, through='RSVPEvent')

    STATUS = Choices('draft', 'published')


class Comment(models.Model):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    parent = models.ForeignKey(
        Post,
        related_name='child',
        on_delete=models.CASCADE,
    )
    downvote = models.ManyToManyField(Profile, through='DownvoteEvent')


class UpvoteEvent(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
    )


class DownvoteEvent(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
    )


class RSVPEvent(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
    )
