from datetime import datetime
from django.db import models
from django.core.validators import MinLengthValidator
from model_utils.models import TimeStampedModel
from annoying.fields import AutoOneToOneField
from ibis.models import Person


class Notifier(models.Model):
    user = AutoOneToOneField(
        Person,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    email_follow = models.BooleanField(default=True)
    email_transaction = models.BooleanField(default=True)
    email_comment = models.BooleanField(default=True)
    email_like = models.BooleanField(default=False)

    last_seen = models.DateTimeField(default=datetime.utcfromtimestamp(0))


class Notification(TimeStampedModel):

    GENERAL_ANNOUNCEMENT = 'GA'
    UBP_DISTRIBUTION = 'UD'
    RECEIVED_FOLLOW = 'RF'
    RECEIVED_TRANSACTION = 'RT'
    RECEIVED_COMMENT = 'RC'
    RECEIVED_LIKE = 'RL'
    FOLLOWING_NEWS = 'FN'
    FOLLOWING_EVENT = 'FE'
    FOLLOWING_POST = 'FP'
    UPCOMING_EVENT = 'UE'

    NOTIFICATION_CATEGORY = (
        (GENERAL_ANNOUNCEMENT, 'General Announcement'),
        (UBP_DISTRIBUTION, 'UBP Distribution'),
        (RECEIVED_FOLLOW, 'Received Follow'),
        (RECEIVED_TRANSACTION, 'Received Transaction'),
        (RECEIVED_COMMENT, 'Received Comment'),
        (RECEIVED_LIKE, 'Received Like'),
        (FOLLOWING_NEWS, 'Following News'),
        (FOLLOWING_EVENT, 'Following Event'),
        (FOLLOWING_POST, 'Following Post'),
        (UPCOMING_EVENT, 'Upcoming Event'),
    )

    notifier = models.ForeignKey(
        Notifier,
        on_delete=models.CASCADE,
    )
    category = models.CharField(
        max_length=2,
        choices=NOTIFICATION_CATEGORY,
    )
    clicked = models.BooleanField(default=False)
    reference = models.TextField(blank=True, null=True)
    description = models.TextField(validators=[MinLengthValidator(1)])


class Email(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
    )

    subject = models.TextField()
    body = models.TextField()
    schedule = models.DateTimeField()
