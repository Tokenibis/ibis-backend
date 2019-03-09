from django.db import models
from profiles.models import Profile

CAT_MAX_LEN = 10
TX_MAX_LEN = 160
TITLE_MAX_LEN = 50
DESC_MAX_LEN = 320


class Nonprofit(models.Model):
    id = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    category = models.CharField(max_length=CAT_MAX_LEN)
    link = models.TextField()
    description = models.TextField()


class Follow(models.Model):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    target = models.OneToOneField(
        Profile,
        related_name='follower',
        on_delete=models.CASCADE,
    )


class Exchange(models.Model):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    is_deposit = models.BooleanField()
    amount = models.PositiveIntegerField()


class Post(models.Model):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )


class Transaction(models.Model):
    id = models.OneToOneField(
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


class Article(models.Model):
    id = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    title = models.CharField(max_length=TITLE_MAX_LEN)

    description = models.CharField(max_length=DESC_MAX_LEN)

    content = ''  # TODO: how to handle this?


class Event(models.Model):
    id = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    title = models.CharField(max_length=TITLE_MAX_LEN)
    link = models.TextField()
    description = models.CharField(max_length=DESC_MAX_LEN)


class Comment(models.Model):
    id = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    parent = models.ForeignKey(
        Post,
        related_name='child',
        on_delete=models.CASCADE,
    )


class Upvote(models.Model):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
    )


class Downvote(models.Model):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
    )


class RSVP(models.Model):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
    )
