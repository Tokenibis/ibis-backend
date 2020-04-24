import os
import json
import random

from django.utils.timezone import now, timedelta
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from graphql_relay.node.node import to_global_id

from notifications.models import Notification, Email
from api.management.commands.loaddata import STATE

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


def _get_submodel(instance, supermodel):
    for submodel in supermodel.__subclasses__():
        if submodel.objects.filter(pk=instance.pk).exists():
            return submodel


# @receiver(post_save, sender=ibis.models.Deposit)
# def handlePersonCreate(sender, instance, created, **kwargs):
#     if not created:
#         return

#     notifier = instance.notifier

#     notification = Notification.objects.create(
#         notifier=notifier,
#         category=Notification.UBP_DISTRIBUTION,
#         reference='{}:{}'.format(
#             ibis.models.Deposit.__name__,
#             to_global_id('DepositNode', instance.pk),
#         ),
#         deduper='deposit:{}'.format(instance.pk),
#         description='Welcome to Ibis!',
#     )

#     Email.objects.create(
#         notification=notification,
#         subject=template['subject'].format(user=str(user)),
#         body=template['body'].format(user=str(user)),
#         schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
#     )


@receiver(post_save, sender=ibis.models.Deposit)
def handleDepositCreate(sender, instance, created, **kwargs):
    if not created:
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
                to_global_id('DepositNode', instance.pk),
            ),
            deduper='deposit:{}'.format(instance.pk),
            description=description,
        )

        template = random.choice(ubp_templates)

        if not STATE['LOADING_DATA'] and notifier.email_ubp:
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
                to_global_id('DepositNode', instance.pk),
            ),
            deduper='deposit:{}'.format(instance.pk),
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
        pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.Transaction)
def handleTransactionCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user
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
            to_global_id('TransactionNode', instance.pk),
        ),
        deduper='transaction:{}'.format(instance.pk),
        description=description,
    )

    template = random.choice(transaction_templates)

    if not STATE['LOADING_DATA'] and notifier.email_transaction:
        Email.objects.create(
            notification=notification,
            subject=template['subject'].format(user=str(user)),
            body=template['body'].format(user=str(user)),
            schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
        )

    Notification.objects.filter(deduper=notification.deduper).exclude(
        pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.Comment)
def handleCommentCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user
    current = instance

    notifications = []

    while hasattr(current, 'comment'):
        parent = current.comment.parent
        notifier = parent.user.ibisuser.notifier
        if notifier not in [x.notifier for x in notifications
                            ] and notifier != user.notifier:
            description = '{} replied to your {}'.format(
                str(user),
                _get_submodel(parent, ibis.models.Entry).__name__.lower(),
            )
            notification = Notification.objects.create(
                notifier=notifier,
                category=Notification.RECEIVED_COMMENT,
                deduper='comment:{}:{}'.format(
                    instance.pk,
                    parent.user.ibisuser.pk,
                ),
                description=description,
            )
            notifications.append(notification)

            template = random.choice(comment_templates)

            if not STATE['LOADING_DATA'] and notifier.email_comment:
                Email.objects.create(
                    notification=notification,
                    subject=template['subject'].format(user=str(user)),
                    body=template['body'].format(user=str(user)),
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )

        current = parent

    ref_type = _get_submodel(current, ibis.models.Entry).__name__
    ref_id = to_global_id('{}Node'.format(ref_type), current.pk)

    if notifications:
        notifications[-1].description = '{} replied to your {}'.format(
            str(user), ref_type.lower())

    for notification in notifications:
        notification.reference = '{}:{}'.format(ref_type, ref_id)
        notification.save()

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.News)
def handleNewsCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} released a news story'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_NEWS,
            reference='{}:{}'.format(
                ibis.models.News.__name__,
                to_global_id('NewsNode', instance.pk),
            ),
            deduper='news:{}:{}'.format(
                instance.pk,
                target.pk,
            ),
            description=description,
        )

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.Event)
def handleEventCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} planned an new event'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_EVENT,
            reference='{}:{}'.format(
                ibis.models.Event.__name__,
                to_global_id('EventNode', instance.pk),
            ),
            deduper='event:{}:{}'.format(
                instance.pk,
                target.pk,
            ),
            description=description,
        )

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.Post)
def handlePostCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} made a new post'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_POST,
            reference='{}:{}'.format(
                ibis.models.Post.__name__,
                to_global_id('PostNode', instance.pk),
            ),
            deduper='post:{}:{}'.format(
                instance.pk,
                target.pk,
            ),
            description=description,
        )

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.pk).delete()


@receiver(post_delete, sender=ibis.models.Transaction)
def handleTransactionDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper='transaction:{}'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.Comment)
def handleCommentDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='comment:{}:'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.News)
def handleNewsDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='news:{}:'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.Event)
def handleEventDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='event:{}:'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.Post)
def handlePostDelete(sender, instance, **kwargs):
    Notification.objects.filter(
        deduper__startswith='post:{}:'.format(instance.pk)).delete()


@receiver(m2m_changed, sender=ibis.models.IbisUser.following.through)
def handleFollowUpdate(sender, instance, action, pk_set, **kwargs):
    instance = ibis.models.IbisUser.objects.get(pk=instance.pk)
    if action == 'post_add':
        for pk in pk_set:
            target = ibis.models.IbisUser.objects.get(pk=pk)
            notifier = target.notifier

            ref_type = _get_submodel(instance, ibis.models.IbisUser).__name__

            description = '{} started following you'.format(str(instance))

            notification = Notification.objects.create(
                notifier=notifier,
                category=Notification.RECEIVED_FOLLOW,
                reference='{}:{}'.format(
                    ref_type,
                    to_global_id('{}Node'.format(ref_type), instance.pk),
                ),
                deduper='follow:{}:{}'.format(
                    instance.pk,
                    target.pk,
                ),
                description=description,
            )

            template = random.choice(follow_templates)

            if not STATE['LOADING_DATA'] and notifier.email_follow:
                Email.objects.create(
                    notification=notification,
                    subject=template['subject'].format(user=str(target)),
                    body=template['body'].format(user=str(target)),
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )

            Notification.objects.filter(deduper=notification.deduper).exclude(
                pk=notification.pk).delete()

    elif action == 'post_remove':
        for pk in pk_set:
            target = ibis.models.IbisUser.objects.get(pk=pk)
            Notification.objects.filter(
                deduper__startswith='follow:{}:{}'.format(
                    instance.pk,
                    target.pk,
                )).delete()


@receiver(m2m_changed, sender=ibis.models.Entry.like.through)
def handleLikeUpdate(sender, instance, action, pk_set, **kwargs):
    instance = ibis.models.Entry.objects.get(pk=instance.pk)
    if action == 'post_add':
        current = instance
        for pk in pk_set:
            user = ibis.models.IbisUser.objects.get(pk=pk)
            notifier = current.user.notifier
            description = '{} liked your {}'.format(
                str(user),
                _get_submodel(instance, ibis.models.Entry).__name__,
            )

            while hasattr(current, 'comment'):
                current = current.comment.parent

            ref_type = _get_submodel(current, ibis.models.Entry).__name__

            notification = Notification.objects.create(
                notifier=notifier,
                category=Notification.RECEIVED_LIKE,
                reference='{}:{}'.format(
                    ref_type,
                    to_global_id('{}Node'.format(ref_type), current.pk),
                ),
                deduper='like:{}:{}'.format(
                    user.pk,
                    instance.pk,
                ),
                description=description,
            )

            Notification.objects.filter(deduper=notification.deduper).exclude(
                pk=notification.pk).delete()

    elif action == 'post_remove':
        for pk in pk_set:
            user = ibis.models.IbisUser.objects.get(pk=pk)
            Notification.objects.filter(
                deduper__startswith='like:{}:{}'.format(
                    user.pk,
                    instance.pk,
                )).delete()
