from django.utils.timezone import now
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from graphql_relay.node.node import to_global_id

from notifications.models import Notification, Email

import ibis.models

# --- Signals --------------------------------------------------------------- #


@receiver(post_save, sender=ibis.models.Transaction)
def handleTransactionCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.person
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
            instance.id,
        ),
        deduper='transaction:{}'.format(instance.id),
        description=description,
    )

    if notifier.email_transaction:
        email = Email.objects.create(
            notification=notification,
            subject=description,
            body='TODO',
            schedule=now(),
        )
        email.save()

    Notification.objects.filter(deduper=notification.deduper).exclude(
        pk=notification.id).delete()


@receiver(post_save, sender=ibis.models.Comment)
def handleCommentCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.person
    current = instance

    description = '{} replied to your comment'.format(str(user))

    notifications = []

    while hasattr(current, 'comment'):
        parent = current.comment.parent
        if hasattr(parent.user, 'person'):
            notifier = parent.user.person.notifier
            if notifier not in [x.notifier for x in notifications] and \
               notifier != user.notifier:
                notification = Notification.objects.create(
                    notifier=notifier,
                    category=Notification.RECEIVED_COMMENT,
                    deduper='comment:{}:{}'.format(
                        instance.id,
                        to_global_id('PersonNode', parent.user.person.id),
                    ),
                    description=description,
                )
                notifications.append(notification)
                if notifier.email_comment:
                    email = Email.objects.create(
                        notification=notification,
                        subject=description,
                        body='TODO',
                        schedule=now(),
                    )
                    email.save()
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
        notifier = target.person.notifier

        description = '{} released a news story'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_NEWS,
            reference='{}:{}'.format(ibis.models.News.__name__, instance.id),
            deduper='news:{}:{}'.format(
                instance.id,
                to_global_id('PersonNode', target.id),
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
        notifier = target.person.notifier

        description = '{} planned an new event'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_EVENT,
            reference='{}:{}'.format(
                ibis.models.Event.__name__,
                instance.id,
            ),
            deduper='event:{}:{}'.format(
                instance.id,
                to_global_id('PersonNode', target.id),
            ),
            description=description,
        )

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


@receiver(post_save, sender=ibis.models.Post)
def handlePostCreate(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    user = instance.user.person

    for target in user.follower.all():
        notifier = target.person.notifier

        description = '{} made a new post'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_POST,
            reference='{}:{}'.format(
                ibis.models.Post.__name__,
                instance.id,
            ),
            deduper='post:{}:{}'.format(
                instance.id,
                to_global_id('PersonNode', target.id),
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
