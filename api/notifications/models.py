import os
import string
import random
import logging

from django.conf import settings
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.core.validators import MinLengthValidator
from django.utils.timezone import localtime
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from model_utils.models import TimeStampedModel
from annoying.fields import AutoOneToOneField
from api.management.commands.loaddata import STATE

import ibis.models

DIR = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)

with open(os.path.join(DIR, 'top_email_templates/body.txt')) as fd:
    top_body_template = fd.read()

with open(os.path.join(DIR, 'top_email_templates/html.html')) as fd:
    top_html_template = fd.read()


def get_submodel(instance, supermodel):
    for submodel in supermodel.__subclasses__():
        if submodel.objects.filter(pk=instance.pk).exists():
            return submodel


class Notifier(models.Model):
    user = AutoOneToOneField(
        ibis.models.User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    email_follow = models.BooleanField(
        verbose_name='follow',
        default=True,
    )
    email_donation = models.BooleanField(
        verbose_name='donation',
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
    email_mention = models.BooleanField(
        verbose_name='mention',
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

    def __str__(self):
        return str(self.user)

    def unseen_count(self):
        return self.notification_set.filter(created__gt=self.last_seen).count()

    def _create_link(self, page):
        assert ':' not in page
        _, _, token = TimestampSigner().sign('notifications:{}'.format(
            self.user.id)).split(":", 2)
        return reverse(
            page, kwargs={
                'pk': self.pk,
                'token': token,
            })

    def create_settings_link(self):
        return self._create_link('settings')

    def create_unsubscribe_link(self):
        return self._create_link('unsubscribe')

    def check_link_token(self, token):
        try:
            TimestampSigner().unsign(
                'notifications:{}:{}'.format(self.user.id, token),
                max_age=60 * 60 * 48)  # Valid for 2 days
        except (BadSignature, SignatureExpired):
            return False
        return True


class Notification(TimeStampedModel):

    notifier = models.ForeignKey(
        Notifier,
        on_delete=models.CASCADE,
    )
    clicked = models.BooleanField(default=False)
    reference = models.TextField(blank=True, null=True)
    description = models.TextField(validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{}:{}'.format(
            self.pk,
            self.notifier.user.username,
        )

    def save(self, *args, **kwargs):
        if STATE['LOADING_DATA']:
            self.clicked = True
        super().save(*args, **kwargs)


class UbpNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Deposit,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        if not STATE['LOADING_DATA'] and self.notifier.email_ubp:
            if self.notifier.email_ubp and self.subject.user.user.deposit_set.filter(
                    category=ibis.models.DepositCategory.objects.get(
                        title='ubp')).count() == 1:
                try:
                    subject, body, html = EmailTemplateWelcome.choose(
                    ).make_email(self, self.subject)
                    Email.objects.create(
                        notification=self,
                        subject=subject,
                        body=body,
                        html=html,
                        schedule=now(),
                        force=True,
                    )
                except IndexError:
                    logger.error('No email template found')
            else:
                try:
                    subject, body, html = EmailTemplateUBP.choose().make_email(
                        self, self.subject)
                    Email.objects.create(
                        notification=self,
                        subject=subject,
                        body=body,
                        html=html,
                        schedule=now() +
                        timedelta(minutes=settings.EMAIL_DELAY),
                    )
                except IndexError:
                    logger.error('No email template found')


class DepositNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Deposit,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        try:
            if not STATE['LOADING_DATA'] and self.notifier.email_deposit:
                subject, body, html = EmailTemplateDeposit.choose().make_email(
                    self, self.subject)
                Email.objects.create(
                    notification=self,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')


class DonationNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Donation,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        try:
            if not STATE['LOADING_DATA'] and self.notifier.email_donation:
                subject, body, html = EmailTemplateDonation.choose(
                ).make_email(self, self.subject)
                Email.objects.create(
                    notification=self,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')


class TransactionNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Transaction,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        try:
            if not STATE['LOADING_DATA'] and self.notifier.email_transaction:
                subject, body, html = EmailTemplateTransaction.choose(
                ).make_email(self, self.subject)
                Email.objects.create(
                    notification=self,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')


class NewsNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.News,
        on_delete=models.CASCADE,
    )


class EventNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Event,
        on_delete=models.CASCADE,
    )


class PostNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Post,
        on_delete=models.CASCADE,
    )


class CommentNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Comment,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        try:
            if not STATE['LOADING_DATA'] and self.notifier.email_comment:
                subject, body, html = EmailTemplateComment.choose().make_email(
                    self, self.subject.parent)
                Email.objects.create(
                    notification=self,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')


class FollowNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.User,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        previous = FollowNotification.objects.exclude(id=self.id).filter(
            notifier=self.notifier,
            subject=self.subject,
        )

        if previous.exists():
            previous.delete()
            return

        try:
            if not STATE['LOADING_DATA'] and self.notifier.email_follow:
                subject, body, html = EmailTemplateFollow.choose().make_email(
                    self)
                Email.objects.create(
                    notification=self,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')


class LikeNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Entry,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        ibis.models.User,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        LikeNotification.objects.exclude(id=self.id).filter(
            notifier=self.notifier,
            subject=self.subject,
            user=self.user,
        ).delete()


class MentionNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Entry,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        try:
            if not STATE['LOADING_DATA'] and self.notifier.email_mention:
                subject, body, html = EmailTemplateMention.choose().make_email(
                    self, self.subject)
                Email.objects.create(
                    notification=self,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')


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
    force = models.BooleanField(default=False)

    def __str__(self):
        return '{}:{}'.format(
            self.pk,
            self.notification.notifier.user.email,
        )


class EmailTemplate(models.Model):
    class Meta:
        abstract = True

    subject = models.TextField()
    body = models.TextField()
    html = models.TextField()
    frequency = models.PositiveIntegerField(default=1)

    def make_email(*args, **kwargs):
        raise NotImplementedError

    def _check_keys(self, subject_keys, content_keys):
        if set([
                x[1] for x in string.Formatter().parse(self.subject)
                if x[1] is not None
        ]) != set(subject_keys):
            raise ValidationError('Subject template has invalid key set')

        if set([
                x[1] for x in string.Formatter().parse(self.body)
                if x[1] is not None
        ]) != set(content_keys):
            raise ValidationError('Body template has invalid key set')

        if set([
                x[1] for x in string.Formatter().parse(self.html)
                if x[1] is not None
        ]) != set(content_keys):
            raise ValidationError('HTML template has invalid key set')

    @classmethod
    def choose(cls):
        return random.choice(list(cls.objects.filter(frequency__gte=1)))

    @staticmethod
    def _apply_top_template(notifier, subject, body, html):
        return (
            subject,
            top_body_template.format(
                user=notifier.user.first_name
                if notifier.user.first_name else notifier.user.last_name,
                content=body,
                settings_link=settings.API_ROOT_PATH +
                notifier.create_settings_link(),
                unsubscribe_link=settings.API_ROOT_PATH +
                notifier.create_unsubscribe_link(),
            ),
            top_html_template.format(
                user=notifier.user.first_name
                if notifier.user.first_name else notifier.user.last_name,
                subject=subject,
                content=html,
                settings_link=settings.API_ROOT_PATH +
                notifier.create_settings_link(),
                unsubscribe_link=settings.API_ROOT_PATH +
                notifier.create_unsubscribe_link(),
            ),
        )


class EmailTemplateWelcome(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['link'])

    def make_email(self, notification, deposit):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(link=settings.APP_ROOT_PATH, ),
            self.html.format(link=settings.APP_ROOT_PATH, ),
        )


class EmailTemplateFollow(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['link'])

    def make_email(self, notification):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                link=settings.APP_LINK_RESOLVER(notification.reference), ),
            self.html.format(
                link=settings.APP_LINK_RESOLVER(notification.reference), ),
        )


class EmailTemplateDeposit(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['amount', 'link'])

    def make_email(self, notification, deposit):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateUBP(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['amount', 'link'])

    def make_email(self, notification, deposit):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                amount='${:.2f}'.format(deposit.amount / 100),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateDonation(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['sender', 'link'])

    def make_email(self, notification, donation):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                sender=str(donation.user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                sender=str(donation.user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateTransaction(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['sender', 'link'])

    def make_email(self, notification, transaction):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                sender=str(transaction.user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                sender=str(transaction.user),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateComment(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['entry_type', 'link'])

    def make_email(self, notification, parent):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                entry_type=get_submodel(
                    parent,
                    ibis.models.Entry,
                ).__name__.lower(),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                entry_type=get_submodel(
                    parent,
                    ibis.models.Entry,
                ).__name__.lower(),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class EmailTemplateMention(EmailTemplate):
    def clean(self):
        super()._check_keys([], ['entry_type', 'link'])

    def make_email(self, notification, entry):
        return EmailTemplate._apply_top_template(
            notification.notifier,
            self.subject,
            self.body.format(
                entry_type=get_submodel(
                    entry,
                    ibis.models.Entry,
                ).__name__.lower(),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
            self.html.format(
                entry_type=get_submodel(
                    entry,
                    ibis.models.Entry,
                ).__name__.lower(),
                link=settings.APP_LINK_RESOLVER(notification.reference),
            ),
        )


class DonationMessage(models.Model):
    description = models.TextField()
    frequency = models.PositiveIntegerField(default=1)
