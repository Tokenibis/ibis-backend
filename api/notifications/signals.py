import os
import json
import random

from django.utils.timezone import now, timedelta
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from graphql_relay.node.node import to_global_id

from notifications.models import Notification, Email

import ibis.models

DIR = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(DIR, 'emails/welcome.json')) as fd:
    welcome_templates = json.load(fd)

with open(os.path.join(DIR, 'emails/deposit.json')) as fd:
    deposit_templates = json.load(fd)

with open(os.path.join(DIR, 'emails/ubp.json')) as fd:
    ubp_templates = json.load(fd)

with open(os.path.join(DIR, 'emails/transaction.json')) as fd:
    transaction_templates = json.load(fd)

with open(os.path.join(DIR, 'emails/comment.json')) as fd:
    comment_templates = json.load(fd)

with open(os.path.join(DIR, 'emails/follow.json')) as fd:
    follow_templates = json.load(fd)

# --- Signals --------------------------------------------------------------- #


@receiver(post_save, sender=ibis.models.Deposit)
def handleDepositCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.ibisuser
    notifier = instance.user.notifier

    if instance.payment_id.split(':')[0] == 'ubp':
        description = 'You have a fresh ${:.2f} waiting for you'.format(
            instance.amount / 100)

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.UBP_DISTRIBUTION,
            reference='{}:{}'.format(
                ibis.models.Deposit.__name__,
                to_global_id('DepositNode', instance.id),
            ),
            deduper='deposit:{}'.format(instance.id),
            description=description,
        )

        template = random.choice(ubp_templates)

        if notifier.email_ubp:
            Email.objects.create(
                notification=notification,
                subject=template['subject'].format(user=str(user)),
                body=template['body'].format(user=str(user)),
                schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
            )
    else:
        description = 'Your deposit of ${:.2f} was successful'.format(
            instance.amount / 100)

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.SUCCESSFUL_DEPOSIT,
            reference='{}:{}'.format(
                ibis.models.Deposit.__name__,
                to_global_id('DepositNode', instance.id),
            ),
            deduper='deposit:{}'.format(instance.id),
            description=description,
            clicked=True,  # the user should have seen the deposit
        )

        template = random.choice(deposit_templates)

        if notifier.email_deposit:
            Email.objects.create(
                notification=notification,
                subject=template['subject'].format(user=str(user)),
                body=template['body'].format(user=str(user)),
                schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
            )

    Notification.objects.filter(deduper=notification.deduper).exclude(
        pk=notification.id).delete()


@receiver(post_save, sender=ibis.models.Transaction)
def handleTransactionCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.ibisuser
    notifier = instance.target.notifier

    description = '{} sent you ${:.2f}'.format(
        str(user),
        instance.amount / 100,
    )

    notification = Notification.objects.create(
        notifier=notifier,
        category=Notification.RECEIVED_TRANSACTION,
        reference='{}:{}'.format(
            ibis.models.Transaction.__name__,
            to_global_id('TransactionNode', instance.id),
        ),
        deduper='transaction:{}'.format(instance.id),
        description=description,
    )

    template = random.choice(transaction_templates)

    if notifier.email_transaction:
        Email.objects.create(
            notification=notification,
            subject=template['subject'].format(user=str(user)),
            body=template['body'].format(user=str(user)),
            schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
        )

    Notification.objects.filter(deduper=notification.deduper).exclude(
        pk=notification.id).delete()


@receiver(post_save, sender=ibis.models.Comment)
def handleCommentCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.ibisuser
    current = instance

    description = '{} replied to your comment'.format(str(user))

    notifications = []

    while hasattr(current, 'comment'):
        parent = current.comment.parent
        if hasattr(parent.user, 'ibisuser'):
            notifier = parent.user.ibisuser.notifier
            if notifier not in [x.notifier for x in notifications] and \
               notifier != user.notifier:
                notification = Notification.objects.create(
                    notifier=notifier,
                    category=Notification.RECEIVED_COMMENT,
                    deduper='comment:{}:{}'.format(
                        instance.id,
                        to_global_id('IbisUserNode', parent.user.ibisuser.id),
                    ),
                    description=description,
                )
                notifications.append(notification)

                template = random.choice(comment_templates)

                if notifier.email_comment:
                    Email.objects.create(
                        notification=notification,
                        subject=template['subject'].format(user=str(user)),
                        body=template['body'].format(user=str(user)),
                        schedule=now() +
                        timedelta(minutes=settings.EMAIL_DELAY),
                    )

        current = parent

    for Subclass in ibis.models.Entry.__subclasses__():
        if Subclass.objects.filter(pk=current.id).exists():
            ref_type = Subclass.__name__
            ref_id = to_global_id('{}Node'.format(ref_type), current.id)
            break

    if notifications:
        notifications[-1].description = '{} replied to your {}'.format(
            str(user), ref_type.lower())

    for notification in notifications:
        notification.reference = '{}:{}'.format(ref_type, ref_id)
        notification.save()

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


@receiver(post_save, sender=ibis.models.News)
def handleNewsCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.nonprofit

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} released a news story'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_NEWS,
            reference='{}:{}'.format(
                ibis.models.News.__name__,
                to_global_id('NewsNode', instance.id),
            ),
            deduper='news:{}:{}'.format(
                instance.id,
                to_global_id('IbisUserNode', target.id),
            ),
            description=description,
        )

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


@receiver(post_save, sender=ibis.models.Event)
def handleEventCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.nonprofit

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} planned an new event'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_EVENT,
            reference='{}:{}'.format(
                ibis.models.Event.__name__,
                to_global_id('EventNode', instance.id),
            ),
            deduper='event:{}:{}'.format(
                instance.id,
                to_global_id('IbisUserNode', target.id),
            ),
            description=description,
        )

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


@receiver(post_save, sender=ibis.models.Post)
def handlePostCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.ibisuser

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} made a new post'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_POST,
            reference='{}:{}'.format(
                ibis.models.Post.__name__,
                to_global_id('PostNode', instance.id),
            ),
            deduper='post:{}:{}'.format(
                instance.id,
                to_global_id('IbisUserNode', target.id),
            ),
            description=description,
        )

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


@receiver(post_delete, sender=ibis.models.Transaction)
def handleTransactionDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper='transaction:{}'.format(instance.id)).delete()


@receiver(post_delete, sender=ibis.models.Comment)
def handleCommentDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='comment:{}:'.format(instance.id)).delete()


@receiver(post_delete, sender=ibis.models.News)
def handleNewsDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='news:{}:'.format(instance.id)).delete()


@receiver(post_delete, sender=ibis.models.Event)
def handleEventDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='event:{}:'.format(instance.id)).delete()


@receiver(post_delete, sender=ibis.models.Post)
def handlePostDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='post:{}:'.format(instance.id)).delete()


@receiver(m2m_changed, sender=ibis.models.IbisUser.following.through)
def handleFollowUpdate(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        for pk in pk_set:
            target = ibis.models.IbisUser.objects.get(pk=pk)
            notifier = target.notifier

            submodel = [
                x for x in ibis.models.IbisUser.__subclasses__()
                if hasattr(instance, x.__name__.lower())
            ][0]

            description = '{} started following you'.format(str(instance))

            notification = Notification.objects.create(
                notifier=notifier,
                category=Notification.RECEIVED_FOLLOW,
                reference='{}:{}'.format(
                    submodel.__name__,
                    to_global_id('{}Node'.format(submodel.__name__), instance.id),
                ),
                deduper='follow:{}:{}'.format(
                    instance.id,
                    target.id,
                ),
                description=description,
            )

            template = random.choice(follow_templates)

            if notifier.email_follow:
                Email.objects.create(
                    notification=notification,
                    subject=template['subject'].format(user=str(target)),
                    body=template['body'].format(user=str(target)),
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )

            Notification.objects.filter(deduper=notification.deduper).exclude(
                pk=notification.id).delete()

    elif action == 'post_remove':
        for pk in pk_set:
            target = ibis.models.IbisUser.objects.get(pk=pk)
            Notification.objects.filter(
                deduper__startswith='follow:{}:{}'.format(
                    instance.id,
                    target.id,
                )).delete()


@receiver(m2m_changed, sender=ibis.models.Entry.like.through)
def handleLikeUpdate(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        notifier = instance.user.notifier

        submodel = [
            x for x in ibis.models.Entry.__subclasses__()
            if hasattr(instance, x.__name__.lower())
        ][0]

        for pk in pk_set:
            user = ibis.models.IbisUser.objects.get(pk=pk)
            description = '{} liked your entry'.format(str(user))

            notification = Notification.objects.create(
                notifier=notifier,
                category=Notification.RECEIVED_LIKE,
                reference='{}:{}'.format(
                    submodel.__name__,
                    to_global_id('{}Node', submodel.__name__),
                ),
                deduper='like:{}:{}'.format(
                    user.id,
                    instance.id,
                ),
                description=description,
            )

            Notification.objects.filter(deduper=notification.deduper).exclude(
                pk=notification.id).delete()

    elif action == 'post_remove':
        for pk in pk_set:
            user = ibis.models.IbisUser.objects.get(pk=pk)
            Notification.objects.filter(
                deduper__startswith='like:{}:{}'.format(
                    user.id,
                    instance.id,
                )).delete()
