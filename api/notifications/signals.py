import logging
import ibis.models
import notifications.models as models

from django.utils.timezone import now, timedelta
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from graphql_relay.node.node import to_global_id
from api.management.commands.loaddata import STATE

logger = logging.getLogger(__name__)


def _get_submodel(instance, supermodel):
    for submodel in supermodel.__subclasses__():
        if submodel.objects.filter(pk=instance.pk).exists():
            return submodel


# def _handleMentionCreate(instance):
#     for user in instance.mention.exclude(id=instance.user.pk).distinct():
#         root_submodel = _get_submodel(
#             instance.get_root(), ibis.models.Entry
#         ) if instance.__class__ == ibis.models.Comment else instance.__class__

#         description = '{} mentioned you in a {}'.format(
#             instance.user,
#             instance.__class__.__name__.lower(),
#         )

#         notification = models.Notification.objects.create(
#             notifier=user.notifier,
#             category=models.Notification.RECEIVED_MENTION,
#             reference='{}:{}'.format(
#                 instance.__class__.__name__,
#                 to_global_id('{}Node'.format(
#                     root_submodel.__name__,
#                     instance.pk,
#                 )),
#             ),
#             deduper='mention:{}:{}'.format(instance.pk, user.pk),
#             description=description,
#         )

#         try:
#             if not STATE['LOADING_DATA'] and user.notifier.email_mention:
#                 subject, body, html = models.EmailTemplateMention.choose(
#                 ).make_email(notification, instance)
#                 models.Email.objects.create(
#                     notification=notification,
#                     subject=subject,
#                     body=body,
#                     html=html,
#                     schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
#                 )
#         except IndexError:
#             logger.error('No email template found')

#         models.Notification.objects.filter(
#             deduper=notification.deduper).exclude(pk=notification.pk).delete()


# def _handleMentionDelete(instance):
#     for user in instance.mention.exclude(id=instance.user.pk).distinct():
#         models.Notification.objects.filter(
#             deduper__startswith='mention:{}:{}'.format(
#                 instance.pk,
#                 user.pk,
#             )).delete()


@receiver(post_save, sender=ibis.models.Deposit)
def handleDepositCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = instance.user.ibisuser
    notifier = instance.user.notifier

    if instance.payment_id.split(':')[0] == 'ubp':
        description = 'You have a fresh ${:.2f} waiting for you'.format(
            instance.amount / 100)

        notification = models.Notification.objects.create(
            notifier=notifier,
            category=models.Notification.UBP_DISTRIBUTION,
            reference='{}:{}'.format(
                ibis.models.Deposit.__name__,
                to_global_id('DepositNode', instance.pk),
            ),
            deduper='deposit:{}'.format(instance.pk),
            description=description,
        )

        if not STATE['LOADING_DATA'] and notifier.email_ubp:
            if notifier.email_ubp and user.deposit_set.filter(
                    category=ibis.models.DepositCategory.objects.get(
                        title='ubp')).count() == 1:
                try:
                    subject, body, html = models.EmailTemplateWelcome.choose(
                    ).make_email(notification, instance)
                    models.Email.objects.create(
                        notification=notification,
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
                    subject, body, html = models.EmailTemplateUBP.choose(
                    ).make_email(notification, instance)
                    models.Email.objects.create(
                        notification=notification,
                        subject=subject,
                        body=body,
                        html=html,
                        schedule=now() +
                        timedelta(minutes=settings.EMAIL_DELAY),
                    )
                except IndexError:
                    logger.error('No email template found')
    else:
        description = 'Your deposit of ${:.2f} was successful'.format(
            instance.amount / 100)

        notification = models.Notification.objects.create(
            notifier=notifier,
            category=models.Notification.SUCCESSFUL_DEPOSIT,
            reference='{}:{}'.format(
                ibis.models.Deposit.__name__,
                to_global_id('DepositNode', instance.pk),
            ),
            deduper='deposit:{}'.format(instance.pk),
            description=description,
        )

        try:
            if not STATE['LOADING_DATA'] and notifier.email_deposit:
                subject, body, html = models.EmailTemplateDeposit.choose(
                ).make_email(notification, instance)
                models.Email.objects.create(
                    notification=notification,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')

    models.Notification.objects.filter(deduper=notification.deduper).exclude(
        pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.Donation)
def handleDonationCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user
    notifier = instance.target.notifier

    description = '{} donated ${:.2f}'.format(
        str(user),
        instance.amount / 100,
    )

    notification = models.Notification.objects.create(
        notifier=notifier,
        category=models.Notification.RECEIVED_DONATION,
        reference='{}:{}'.format(
            ibis.models.Donation.__name__,
            to_global_id('DonationNode', instance.pk),
        ),
        deduper='donation:{}'.format(instance.pk),
        description=description,
    )

    try:
        if not STATE['LOADING_DATA'] and notifier.email_donation:
            subject, body, html = models.EmailTemplateDonation.choose(
            ).make_email(notification, instance)
            models.Email.objects.create(
                notification=notification,
                subject=subject,
                body=body,
                html=html,
                schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
            )
    except IndexError:
        logger.error('No email template found')

    models.Notification.objects.filter(deduper=notification.deduper).exclude(
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

    notification = models.Notification.objects.create(
        notifier=notifier,
        category=models.Notification.RECEIVED_TRANSACTION,
        reference='{}:{}'.format(
            ibis.models.Transaction.__name__,
            to_global_id('TransactionNode', instance.pk),
        ),
        deduper='transaction:{}'.format(instance.pk),
        description=description,
    )

    try:
        if not STATE['LOADING_DATA'] and notifier.email_transaction:
            subject, body, html = models.EmailTemplateTransaction.choose(
            ).make_email(notification, instance)
            models.Email.objects.create(
                notification=notification,
                subject=subject,
                body=body,
                html=html,
                schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
            )
    except IndexError:
        logger.error('No email template found')

    models.Notification.objects.filter(deduper=notification.deduper).exclude(
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
        notifiers = [parent.user.ibisuser.notifier]
        if _get_submodel(parent, ibis.models.Entry) == ibis.models.Donation:
            notifiers.append(parent.donation.target.ibisuser.notifier)
        if _get_submodel(parent, ibis.models.Entry) == ibis.models.Transaction:
            notifiers.append(parent.transaction.target.ibisuser.notifier)

        for notifier in notifiers:
            if notifier not in [x[0].notifier for x in notifications
                                ] and notifier != user.notifier:
                description = '{} replied to your {}'.format(
                    str(user),
                    _get_submodel(parent, ibis.models.Entry).__name__.lower(),
                )
                notification = models.Notification.objects.create(
                    notifier=notifier,
                    category=models.Notification.RECEIVED_COMMENT,
                    deduper='comment:{}:{}'.format(
                        instance.pk,
                        notifier.pk,
                    ),
                    description=description,
                )
                notifications.append([notification, parent])

        current = parent

    ref_type = _get_submodel(current, ibis.models.Entry).__name__
    ref_id = to_global_id('{}Node'.format(ref_type), current.pk)

    if notifications:
        notifications[-1][0].description = '{} replied to your {}'.format(
            str(user), ref_type.lower())

    for notification, parent in notifications:
        notification.reference = '{}:{}'.format(ref_type, ref_id)

        try:
            if not STATE[
                    'LOADING_DATA'] and notification.notifier.email_comment:
                subject, body, html = models.EmailTemplateComment.choose(
                ).make_email(notification, parent)
                models.Email.objects.create(
                    notification=notification,
                    subject=subject,
                    body=body,
                    html=html,
                    schedule=now() + timedelta(minutes=settings.EMAIL_DELAY),
                )
        except IndexError:
            logger.error('No email template found')

        notification.save()
        models.Notification.objects.filter(
            deduper=notification.deduper).exclude(pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.News)
def handleNewsCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} released a news story'.format(str(user))

        notification = models.Notification.objects.create(
            notifier=notifier,
            category=models.Notification.FOLLOWING_NEWS,
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

        models.Notification.objects.filter(
            deduper=notification.deduper).exclude(pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.Event)
def handleEventCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} planned an new event'.format(str(user))

        notification = models.Notification.objects.create(
            notifier=notifier,
            category=models.Notification.FOLLOWING_EVENT,
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

        models.Notification.objects.filter(
            deduper=notification.deduper).exclude(pk=notification.pk).delete()


@receiver(post_save, sender=ibis.models.Post)
def handlePostCreate(sender, instance, created, **kwargs):
    if not created:
        return

    user = ibis.models.Entry.objects.get(pk=instance.pk).user

    for target in user.follower.all():
        notifier = target.ibisuser.notifier

        description = '{} made a new post'.format(str(user))

        notification = models.Notification.objects.create(
            notifier=notifier,
            category=models.Notification.FOLLOWING_POST,
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

        models.Notification.objects.filter(
            deduper=notification.deduper).exclude(pk=notification.pk).delete()


@receiver(post_delete, sender=ibis.models.Donation)
def handleDonationDelete(sender, instance, **kwargs):
    models.Notification.objects.filter(
        deduper='donation:{}'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.Transaction)
def handleTransactionDelete(sender, instance, **kwargs):
    models.Notification.objects.filter(
        deduper='transaction:{}'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.Comment)
def handleCommentDelete(sender, instance, **kwargs):
    models.Notification.objects.filter(
        deduper__startswith='comment:{}:'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.News)
def handleNewsDelete(sender, instance, **kwargs):
    models.Notification.objects.filter(
        deduper__startswith='news:{}:'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.Event)
def handleEventDelete(sender, instance, **kwargs):
    models.Notification.objects.filter(
        deduper__startswith='event:{}:'.format(instance.pk)).delete()


@receiver(post_delete, sender=ibis.models.Post)
def handlePostDelete(sender, instance, **kwargs):
    models.Notification.objects.filter(
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

            notification = models.Notification.objects.create(
                notifier=notifier,
                category=models.Notification.RECEIVED_FOLLOW,
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

            try:
                if not STATE['LOADING_DATA'] and notifier.email_follow:
                    subject, body, html = models.EmailTemplateFollow.choose(
                    ).make_email(notification)
                    models.Email.objects.create(
                        notification=notification,
                        subject=subject,
                        body=body,
                        html=html,
                        schedule=now() +
                        timedelta(minutes=settings.EMAIL_DELAY),
                    )
            except IndexError:
                logger.error('No email template found')

            models.Notification.objects.filter(
                deduper=notification.deduper).exclude(
                    pk=notification.pk).delete()

    elif action == 'post_remove':
        for pk in pk_set:
            target = ibis.models.IbisUser.objects.get(pk=pk)
            models.Notification.objects.filter(
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

            notification = models.Notification.objects.create(
                notifier=notifier,
                category=models.Notification.RECEIVED_LIKE,
                reference='{}:{}'.format(
                    ref_type,
                    to_global_id('{}Node'.format(ref_type), current.pk),
                ),
                deduper='like:{}:{}:{}'.format(
                    user.pk,
                    instance.pk,
                    instance.user.pk,
                ),
                description=description,
            )

            models.Notification.objects.filter(
                deduper=notification.deduper).exclude(
                    pk=notification.pk).delete()

    elif action == 'post_remove':
        for pk in pk_set:
            user = ibis.models.IbisUser.objects.get(pk=pk)
            models.Notification.objects.filter(
                deduper__startswith='like:{}:{}'.format(
                    user.pk,
                    instance.pk,
                )).delete()
