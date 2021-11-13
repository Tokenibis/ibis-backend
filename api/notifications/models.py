import os
import string
import random
import logging
import markdown
import ibis.models

from django.core.mail import EmailMultiAlternatives
from graphql_relay.node.node import to_global_id
from django.conf import settings
from django.utils.timezone import localtime, timedelta
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.core.validators import MinLengthValidator
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from model_utils.models import TimeStampedModel
from annoying.fields import AutoOneToOneField
from api.management.commands.loaddata import STATE
from api.utils import get_submodel

DIR = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger(__name__)

with open(os.path.join(DIR, 'messages/body.txt')) as fd:
    top_body_template = fd.read()

with open(os.path.join(DIR, 'messages/html.html')) as fd:
    top_html_template = fd.read()

with open(os.path.join(DIR, 'messages/emails.txt')) as fd:
    parts = fd.read().split('***')[1:]
    email_templates = {
        parts[i].split(':')[0]: {
            'subject': parts[i].split(':')[1],
            'body': [x.strip() for x in parts[i + 1].split('---')],
        }
        for i in range(0, len(parts), 2)
    }


def send_email(destinations, subject, body, html, notifier):
    msg = EmailMultiAlternatives(
        subject,
        body,
        'Token Ibis<{}>'.format(settings.EMAIL_HOST_USER),
        destinations,
        headers={
            'List-Unsubscribe':
            '<mailto: {}>, <{}{}>'.format(
                settings.UNSUBSCRIBE_EMAIL,
                settings.API_ROOT_PATH,
                notifier.create_unsubscribe_link(),
            ),
        },
    )
    msg.attach_alternative(html, 'text/html')
    msg.send()


class Notifier(models.Model):
    user = AutoOneToOneField(
        ibis.models.User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    email_message = models.BooleanField(
        verbose_name='message',
        default=True,
    )
    email_donation = models.BooleanField(
        verbose_name='donation',
        default=True,
    )
    email_reward = models.BooleanField(
        verbose_name='reward',
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
    email_deposit = models.BooleanField(
        verbose_name='deposit',
        default=True,
    )
    email_withdrawal = models.BooleanField(
        verbose_name='withdrawal',
        default=True,
    )
    email_grant = models.BooleanField(
        verbose_name='grant',
        default=True,
    )
    email_like = models.BooleanField(
        verbose_name='like',
        default=False,
    )

    last_seen = models.DateTimeField(default=localtime().replace(
        year=2019,
        month=4,
        day=5,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ))

    tutorial = models.BooleanField(default=True)

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

    def create_email(self, subject, body, force=False):
        if not STATE['LOADING_DATA']:
            Email.objects.create(
                notification=self,
                subject=subject,
                body=top_body_template.format(
                    user=self.notifier.user.first_name,
                    content=body,
                    settings_link=settings.API_ROOT_PATH +
                    self.notifier.create_settings_link(),
                    unsubscribe_link=settings.API_ROOT_PATH +
                    self.notifier.create_unsubscribe_link(),
                ),
                html=top_html_template.format(
                    user=self.notifier.user.first_name,
                    subject=subject,
                    content=markdown.markdown(body).replace(
                        '<a href=',
                        '<a style="color: #84ab3f" href=',
                    ),
                    settings_link=settings.API_ROOT_PATH +
                    self.notifier.create_settings_link(),
                    unsubscribe_link=settings.API_ROOT_PATH +
                    self.notifier.create_unsubscribe_link(),
                ),
                schedule=localtime() +
                timedelta(minutes=0 if force else settings.EMAIL_DELAY),
                force=force,
            )


class MessageDirectNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.MessageDirect,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        if self.notifier.email_message:
            self.create_email(
                email_templates['MessageDirect']['subject'],
                random.choice(email_templates['MessageDirect']['body']).format(
                    sender=str(self.subject.user),
                    link=settings.APP_LINK_RESOLVER(self.reference),
                ),
            )


class MessageChannelNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.MessageChannel,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        if self.notifier.email_message:
            self.create_email(
                email_templates['MessageChannel']['subject'],
                random.choice(
                    email_templates['MessageChannel']['body']).format(
                        sender=str(self.subject.user),
                        link=settings.APP_LINK_RESOLVER(self.reference),
                    ),
            )


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

        if not self.notifier.user.deposit_set.count() > 1:
            self.create_email(
                email_templates['Welcome']['subject'],
                random.choice(email_templates['Welcome']['body']).format(
                    link=settings.APP_LINK_RESOLVER()),
                force=True,
            )
        elif self.notifier.email_deposit:
            body = random.choice(email_templates['Deposit']['body']).format(
                amount='${:,.2f}'.format(self.subject.amount / 100),
                link=settings.APP_LINK_RESOLVER(),
            )

            time = localtime()

            feed = []

            for x in ibis.models.Organization.objects.filter(
                    date_joined__gte=time - timedelta(days=7)):
                feed.append(
                    'Please welcome our newest nonprofit: [{}]({}).'.format(
                        x,
                        settings.APP_LINK_RESOLVER('{}:{}'.format(
                            ibis.models.Organization.__name__,
                            to_global_id('UserNode', x.pk),
                        )),
                    ))
            for x in ibis.models.News.objects.filter(
                    created__gte=time - timedelta(days=7)):
                feed.append('{} just published an article: [{}]({})'.format(
                    x.user,
                    x.title,
                    settings.APP_LINK_RESOLVER('{}:{}'.format(
                        ibis.models.News.__name__,
                        to_global_id('EntryNode', x.pk),
                    )),
                ))
            for x in ibis.models.Event.objects.filter(date__gte=time).filter(
                    date__lt=time + timedelta(days=14)):
                feed.append('{}\'s event, [{}]({}), is coming up on {}'.format(
                    x.user,
                    x.title,
                    settings.APP_LINK_RESOLVER('{}:{}'.format(
                        ibis.models.Event.__name__,
                        to_global_id('EntryNode', x.pk),
                    )),
                    x.date.strftime('%B %d'),
                ))
            for x in ibis.models.Post.objects.filter(
                    created__gte=time - timedelta(days=7)):
                feed.append('{} just made a post: [{}]({})'.format(
                    x.user,
                    x.title,
                    settings.APP_LINK_RESOLVER('{}:{}'.format(
                        ibis.models.Post.__name__,
                        to_global_id('EntryNode', x.pk),
                    )),
                ))

            for x in ibis.models.Bot.objects.filter(
                    date_joined__gte=time - timedelta(days=7)):
                feed.append('Please welcome our newest bot: [{}]({}).'.format(
                    x,
                    settings.APP_LINK_RESOLVER('{}:{}'.format(
                        ibis.models.Bot.__name__,
                        to_global_id('UserNode', x.pk),
                    )),
                ))

            if feed:
                body = '{}\n\n__This week on Token Ibis:__\n\n* {}'.format(
                    body,
                    '\n\n* '.join(feed),
                )

            self.create_email(
                email_templates['Deposit']['subject'],
                body,
            )


class WithdrawalNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Withdrawal,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        self.create_email(
            email_templates['Withdrawal']['subject'],
            random.choice(email_templates['Withdrawal']['body']).format(
                amount='${:,.2f}'.format(self.subject.amount / 100),
                link=settings.APP_LINK_RESOLVER(self.reference),
            ),
        )


class GrantNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Grant,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        if self.notifier.email_grant:
            self.create_email(
                email_templates['Grant']['subject'],
                random.choice(email_templates['Grant']['body']).format(
                    amount='${:,.2f}'.format(self.subject.amount / 100),
                    link=settings.APP_LINK_RESOLVER(self.reference),
                ),
            )


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

        if self.notifier.email_donation:
            self.create_email(
                email_templates['Donation']['subject'],
                random.choice(email_templates['Donation']['body']).format(
                    sender=str(self.subject.user),
                    link=settings.APP_LINK_RESOLVER(self.reference),
                ),
            )


class RewardNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Reward,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:
            return

        if self.notifier.email_reward:
            self.create_email(
                email_templates['Reward']['subject'],
                random.choice(email_templates['Reward']['body']).format(
                    sender=str(self.subject.user),
                    link=settings.APP_LINK_RESOLVER(self.reference),
                ),
            )


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


class ActivityNotification(Notification):
    subject = models.ForeignKey(
        ibis.models.Activity,
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

        if self.notifier.email_comment:
            self.create_email(
                email_templates['Comment']['subject'],
                random.choice(email_templates['Comment']['body']).format(
                    entry_type=get_submodel(
                        self.subject.parent).__name__.lower(),
                    link=settings.APP_LINK_RESOLVER(self.reference),
                ),
            )


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

        if self.notifier.email_mention:
            self.create_email(
                email_templates['Mention']['subject'],
                random.choice(email_templates['Mention']['body']).format(
                    entry_type=get_submodel(self.subject).__name__.lower(),
                    link=settings.APP_LINK_RESOLVER(self.reference),
                ),
            )


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
        null=True,
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

    @classmethod
    def choose(cls):
        return random.choice(list(cls.objects.filter(frequency__gte=1)))

    @staticmethod
    def _apply_top_template(notifier, subject, body):
        return (
            subject,
            top_body_template.format(
                user=notifier.user.first_name,
                content=body,
                settings_link=settings.API_ROOT_PATH +
                notifier.create_settings_link(),
                unsubscribe_link=settings.API_ROOT_PATH +
                notifier.create_unsubscribe_link(),
            ),
            top_html_template.format(
                user=notifier.user.first_name,
                subject=subject,
                content=markdown.markdown(body).replace(
                    '<a href=',
                    '<a style="color: #84ab3f" href=',
                ),
                settings_link=settings.API_ROOT_PATH +
                notifier.create_settings_link(),
                unsubscribe_link=settings.API_ROOT_PATH +
                notifier.create_unsubscribe_link(),
            ),
        )


class DonationMessage(models.Model):
    description = models.TextField()
    frequency = models.PositiveIntegerField(default=1)
