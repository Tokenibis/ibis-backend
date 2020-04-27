import os
import string
import random

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.core.validators import MinLengthValidator
from django.utils.timezone import localtime, now
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from model_utils.models import TimeStampedModel
from annoying.fields import AutoOneToOneField

import ibis.models

DIR = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(DIR, 'top_email_templates/body.txt')) as fd:
    top_body_template = fd.read()

with open(os.path.join(DIR, 'top_email_templates/html.html')) as fd:
    top_html_template = fd.read()


def _get_submodel(instance, supermodel):
    for submodel in supermodel.__subclasses__():
        if submodel.objects.filter(pk=instance.pk).exists():
            return submodel


class Notifier(models.Model):
    user = AutoOneToOneField(
        ibis.models.IbisUser,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    WEEKLY = 'WE'
    DAILY = 'DA'
    INSTANTLY = 'IN'
    NEVER = 'NE'

    FREQUENCY = (
        (WEEKLY, 'weekly'),
        (DAILY, 'daily'),
        (INSTANTLY, 'instantly'),
        (NEVER, 'never'),
    )

    email_follow = models.BooleanField(
        verbose_name='follow',
        default=True,
    )
    email_transaction = models.BooleanField(
        verbose_name='transaction',
        default=True,
    )
    email_comment = models.BooleanField(
        verbose_name='comment',
        default=True,
    )
    email_ubp = models.BooleanField(
        verbose_name='ubp',
        default=True,
    )
    email_deposit = models.BooleanField(
        verbose_name='deposit',
        default=True,
    )
    email_like = models.BooleanField(
        verbose_name='like',
        default=False,
    )
    email_feed = models.CharField(
        verbose_name='feed',
        max_length=2,
        choices=FREQUENCY,
        default=WEEKLY,
    )

    last_seen = models.DateTimeField(
        default=localtime(now()).replace(
            year=2019,
            month=4,
            day=5,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ))

    def unseen_count(self):
        return self.notification_set.filter(created__gt=self.last_seen).count()

    def _create_link(self, link):
        username, token = TimestampSigner().sign(self.user.username).split(
            ":", 1)
        return reverse(
            link, kwargs={
                'pk': self.pk,
                'token': token,
            })

    def create_settings_link(self):
        return self._create_link('settings')

    def create_unsubscribe_link(self):
        return self._create_link('unsubscribe')

    def check_link_token(self, token):
        try:
            key = '%s:%s' % (self.user.username, token)
            TimestampSigner().unsign(
                key, max_age=60 * 60 * 48)  # Valid for 2 days
        except (BadSignature, SignatureExpired):
            return False
        return True


class Notification(TimeStampedModel):

    GENERAL_ANNOUNCEMENT = 'GA'
    UBP_DISTRIBUTION = 'UD'
    SUCCESSFUL_DEPOSIT = 'SD'
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
        (SUCCESSFUL_DEPOSIT, 'Successful Deposit'),
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
    deduper = models.TextField(blank=True, null=True)
    description = models.TextField(validators=[MinLengthValidator(1)])


class Email(models.Model):

    SCHEDULED = 'SC'
    STALE = 'ST'
    ATTEMPTING = 'SC'
    FAILED = 'FA'
    UNNEEDED = 'UN'
    SUCCEEDED = 'SU'

    EMAIL_STATUS = (
        (SCHEDULED, 'Scheduled'),
        (STALE, 'Stale'),
        (FAILED, 'Failed'),
        (UNNEEDED, 'Unneeded'),
        (SUCCEEDED, 'Succeeded'),
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
    )

    subject = models.TextField()
    body = models.TextField()
    html = models.TextField()
    schedule = models.DateTimeField()
    status = models.CharField(
        max_length=2,
        choices=EMAIL_STATUS,
        default=SCHEDULED,
    )


class EmailTemplate(models.Model):
    class Meta:
        abstract = True

    subject = models.TextField()
    body = models.TextField()
    html = models.TextField()
    active = models.BooleanField(default=True)

    def make_email(*args, **kwargs):
        raise NotImplementedError

    def _check_keys(self, subject_keys, content_keys):
        if set([
                x[1] for x in string.Formatter().parse(self.subject)
                if x[1] is not None
        ]) == set(subject_keys):
            raise ValidationError('Subject template has invalid key set')

        if set([
                x[1] for x in string.Formatter().parse(self.body)
                if x[1] is not None
        ]) == set(content_keys):
            raise ValidationError('Body template has invalid key set')

        if set([
                x[1] for x in string.Formatter().parse(self.html)
                if x[1] is not None
        ]) == set(content_keys):
            raise ValidationError('HTML template has invalid key set')

    @classmethod
    def choose(cls):
        return random.choice(list(cls.objects.filter(active=True)))

    @staticmethod
    def _apply_top_template(notifier, subject, body, html):
        return (
            subject,
            top_body_template.format(
                content=body,
                settings_link=notifier.create_settings_link(),
                unsubscribe_link=notifier.create_unsubscribe_link(),
            ),
            top_html_template.format(
                subject=subject,
                content=body,
                settings_link=notifier.create_settings_link(),
                unsubscribe_link=notifier.create_unsubscribe_link(),
            ),
        )


class EmailTemplateWelcome(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['user'])

    def make_email(self, notification, deposit):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(user=str(deposit.user)),
            self.html.format(user=str(deposit.user)),
        )


class EmailTemplateFollow(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['user', 'link'])

    def make_email(self, notification, user):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                user=str(user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                user=str(user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateDeposit(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['user', 'amount', 'link'])

    def make_email(self, notification, deposit):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                user=str(deposit.user),
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                user=str(deposit.user),
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateUBP(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['user', 'amount', 'link'])

    def make_email(self, notification, deposit):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                user=str(deposit.user),
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                user=str(deposit.user),
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateTransaction(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['user', 'sender', 'link'])

    def make_email(self, notification, transaction):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                user=str(transaction.target),
                sender=str(transaction.user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                user=str(transaction.user),
                sender=str(transaction.user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateComment(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['user', 'entry_type', 'link'])

    def make_email(self, notification, parent):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                user=str(parent.user),
                entry_type=_get_submodel(
                    parent,
                    ibis.models.Entry,
                ).__name__.lower(),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                user=str(parent.user),
                entry_type=_get_submodel(
                    parent,
                    ibis.models.Entry,
                ).__name__.lower(),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )
