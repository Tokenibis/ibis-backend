import logging
import ibis.models
import notifications.models as models

from django.conf import settings
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from graphql_relay.node.node import to_global_id
from api.utils import get_submodel
from api.management.commands.loaddata import STATE

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ibis.models.Person)
def handlePersonCreate(sender, instance, created, raw, **kwargs):
    if STATE['LOADING_DATA'] or raw or not created:
        return

    try:
        subject, body, html = models.EmailTemplateWelcome.choose().make_email(
            instance.notifier)
        if settings.EMAIL_ACTIVE and instance.user.email:
            models.send_email(
                [instance.user.email],
                subject,
                body,
                html,
                instance.notifier,
            )
    except IndexError:
        logger.error('No email template found')


@receiver(post_save, sender=ibis.models.Deposit)
def handleDepositCreate(sender, instance, created, **kwargs):
    if not created:
        return

    if ibis.models.ExchangeCategory.objects.filter(title='ubp').exists(
    ) and instance.category == ibis.models.ExchangeCategory.objects.get(
            title='ubp'):
        description = 'You have a fresh ${:.2f} waiting for you'.format(
            instance.amount / 100)

        models.DepositNotification.objects.create(
            notifier=instance.user.notifier,
            reference='{}:{}'.format(
                ibis.models.Deposit.__name__,
                to_global_id('DepositNode', instance.pk),
            ),
            description=description,
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Withdrawal)
def handleWithdrawalCreate(sender, instance, created, **kwargs):
    if not created:
        return

    description = 'Token Ibis has processed a withdrawal of ${:.2f}'.format(
        instance.amount / 100)

    models.WithdrawalNotification.objects.create(
        notifier=instance.user.notifier,
        reference='{}:{}'.format(
            ibis.models.Withdrawal.__name__,
            to_global_id('WithdrawalNode', instance.pk),
        ),
        description=description,
        subject=instance,
        created=instance.created,
    )


@receiver(post_save, sender=ibis.models.Grant)
def handleGrantCreate(sender, instance, created, **kwargs):
    if not created:
        return


    if instance.user:
        description = 'Your grant of ${:.2f} has been received'.format(
            instance.amount / 100)

        models.GrantNotification.objects.create(
            notifier=instance.user.notifier,
            reference='{}:{}'.format(
                ibis.models.Grant.__name__,
                to_global_id('GrantNode', instance.pk),
            ),
            description=description,
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Donation)
def handleDonationCreate(sender, instance, created, **kwargs):
    if not created:
        return

    reference = '{}:{}'.format(
        ibis.models.Donation.__name__,
        to_global_id('EntryNode', instance.pk),
    )

    models.DonationNotification.objects.create(
        notifier=instance.target.notifier,
        reference=reference,
        description='{} donated ${:.2f}'.format(
            str(instance.user),
            instance.amount / 100,
        ),
        subject=instance,
        created=instance.created,
    )


@receiver(post_save, sender=ibis.models.Reward)
def handleRewardCreate(sender, instance, created, **kwargs):
    if not created:
        return

    reference = '{}:{}'.format(
        ibis.models.Reward.__name__,
        to_global_id('EntryNode', instance.pk),
    )

    models.RewardNotification.objects.create(
        notifier=instance.target.notifier,
        reference=reference,
        description='{} sent you ${:.2f}'.format(
            str(instance.user),
            instance.amount / 100,
        ),
        subject=instance,
        created=instance.created,
    )


@receiver(post_save, sender=ibis.models.News)
def handleNewsCreate(sender, instance, created, **kwargs):
    if not created:
        return

    reference = '{}:{}'.format(
        ibis.models.News.__name__,
        to_global_id('EntryNode', instance.pk),
    )

    for target in instance.user.follower.all():
        models.NewsNotification.objects.create(
            notifier=target.user.notifier,
            reference=reference,
            description='{} released a news story'.format(str(instance.user)),
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Event)
def handleEventCreate(sender, instance, created, **kwargs):
    if not created:
        return

    reference = '{}:{}'.format(
        ibis.models.Event.__name__,
        to_global_id('EntryNode', instance.pk),
    )

    for target in instance.user.follower.all():
        models.EventNotification.objects.create(
            notifier=target.user.notifier,
            reference=reference,
            description='{} planned an new event'.format(str(instance.user)),
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Post)
def handlePostCreate(sender, instance, created, **kwargs):
    if not created:
        return

    reference = '{}:{}'.format(
        ibis.models.Post.__name__,
        to_global_id('EntryNode', instance.pk),
    )

    for target in instance.user.follower.all():
        notifier = target.user.notifier
        models.PostNotification.objects.create(
            notifier=notifier,
            reference=reference,
            description='{} made a new post'.format(str(instance.user)),
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Activity)
def handleActivityCreate(sender, instance, created, **kwargs):
    if not created:
        return

    reference = '{}:{}'.format(
        ibis.models.Activity.__name__,
        to_global_id('EntryNode', instance.pk),
    )

    for target in instance.user.follower.all():
        notifier = target.user.notifier
        models.ActivityNotification.objects.create(
            notifier=notifier,
            reference=reference,
            description='{} issued a new activity'.format(str(instance.user)),
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Comment)
def handleCommentCreate(sender, instance, created, **kwargs):
    if not created:
        return

    current = instance

    notification_info = []

    while hasattr(current, 'comment'):
        parent = current.comment.parent
        notifiers = [
            get_submodel(parent).objects.get(pk=parent.pk).user.notifier
        ]
        if get_submodel(parent) == ibis.models.Donation:
            notifiers.append(parent.donation.target.user.notifier)
        if get_submodel(parent) == ibis.models.Reward:
            notifiers.append(parent.reward.target.user.notifier)

        for notifier in notifiers:
            if notifier not in [x['notifier'] for x in notification_info
                                ] and notifier != instance.user.notifier:
                description = '{} replied to your {}'.format(
                    str(instance.user),
                    get_submodel(parent).__name__.lower(),
                )
                notification_info.append({
                    'notifier': notifier,
                    'description': description,
                    'subject': instance,
                })

        current = parent

    ref_type = get_submodel(current).__name__
    ref_id = to_global_id('{}Node'.format(ref_type), current.pk)
    reference = '{}:{}'.format(ref_type, ref_id)

    if notification_info:
        notification_info[-1]['description'] = '{} replied to your {}'.format(
            str(instance.user), ref_type.lower())

    for info in notification_info:
        models.CommentNotification.objects.create(
            notifier=info['notifier'],
            reference=reference,
            description=info['description'],
            subject=info['subject'],
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.MessageDirect)
def handleMessageDirectCreate(sender, instance, created, **kwargs):
    if not created:
        return

    description = 'You have a new direct message from {}'.format(
        str(instance.user))

    models.MessageDirectNotification.objects.create(
        notifier=instance.target.notifier,
        reference='{}:{}'.format(
            ibis.models.MessageDirect.__name__,
            to_global_id('UserNode', instance.user.id),
        ),
        description=description,
        subject=instance,
        created=instance.created,
    )

    # If a user responds, assumed they've "seen" all previous messages
    for prev_message in ibis.models.MessageDirect.objects.filter(
            user=instance.target, target=instance.user):
        for prev_notification in models.MessageDirectNotification.objects.filter(
                subject=prev_message, clicked=False):
            prev_notification.clicked = True
            prev_notification.save()


@receiver(post_save, sender=ibis.models.MessageChannel)
def handleMessageChannelCreate(sender, instance, created, **kwargs):
    if not created:
        return

    description = 'You have a new channel message from {}'.format(
        str(instance.user))

    for subscriber in instance.target.subscriber.exclude(id=instance.user.id):
        models.MessageChannelNotification.objects.create(
            notifier=subscriber.notifier,
            reference='{}:{}'.format(
                ibis.models.MessageChannel.__name__,
                to_global_id('ChannelNode', instance.target.id),
            ),
            description=description,
            subject=instance,
            created=instance.created,
        )

    # If a user responds, assumed they've "seen" all previous messages
    for prev_message in ibis.models.MessageChannel.objects.filter(
            target=instance.target):
        for prev_notification in models.MessageChannelNotification.objects.filter(
                notifier__user=instance.user,
                subject=prev_message,
                clicked=False,
        ):
            prev_notification.clicked = True
            prev_notification.save()


@receiver(m2m_changed, sender=ibis.models.User.following.through)
def handleFollowUpdate(sender, instance, action, pk_set, **kwargs):
    user = ibis.models.User.objects.get(pk=instance.pk)
    if action == 'post_add':
        for pk in pk_set:
            target = ibis.models.User.objects.get(pk=pk)
            notifier = target.notifier

            ref_type = get_submodel(user).__name__

            description = '{} started following you'.format(str(user))

            models.FollowNotification.objects.create(
                notifier=notifier,
                reference='{}:{}'.format(
                    ref_type,
                    to_global_id('{}Node'.format(ref_type), user.pk),
                ),
                description=description,
                subject=user,
            )

    elif action == 'post_remove':
        for pk in pk_set:
            models.FollowNotification.objects.filter(
                notifier=ibis.models.User.objects.get(pk=pk).notifier,
                subject=user,
            ).delete()


@receiver(m2m_changed, sender=ibis.models.Entry.like.through)
def handleLikeUpdate(sender, instance, action, pk_set, **kwargs):
    entry = ibis.models.Entry.objects.get(pk=instance.pk)
    if action == 'post_add':
        for pk in pk_set:
            user = ibis.models.User.objects.get(pk=pk)
            notifier = get_submodel(entry).objects.get(
                pk=instance.pk).user.notifier
            description = '{} liked your {}'.format(
                str(user),
                get_submodel(entry).__name__.lower(),
            )

            root = entry
            while get_submodel(root) == ibis.models.Comment:
                root = root.comment.parent

            ref_type = get_submodel(root).__name__

            models.LikeNotification.objects.create(
                notifier=notifier,
                reference='{}:{}'.format(
                    ref_type,
                    to_global_id('{}Node'.format(ref_type), root.pk),
                ),
                description=description,
                subject=entry,
                user=user,
            )

    elif action == 'post_remove':
        for pk in pk_set:
            notifier = get_submodel(entry).objects.get(
                pk=instance.pk).user.notifier
            models.LikeNotification.objects.filter(
                notifier=notifier,
                subject=entry,
                user=ibis.models.User.objects.get(pk=pk),
            ).delete()


@receiver(m2m_changed, sender=ibis.models.Entry.mention.through)
def handleMentionUpdate(sender, instance, action, pk_set, **kwargs):
    entry = ibis.models.Entry.objects.get(pk=instance.pk)
    if action == 'post_add':
        for pk in pk_set:
            if not ibis.models.User.objects.get(pk=pk).can_see(entry):
                continue
            description = '{} mentioned you in their {}'.format(
                get_submodel(entry).objects.get(pk=instance.pk).user,
                get_submodel(entry).__name__.lower(),
            )

            root = entry
            while get_submodel(root) == ibis.models.Comment:
                root = root.comment.parent

            ref_type = get_submodel(root).__name__

            models.MentionNotification.objects.create(
                notifier=ibis.models.User.objects.get(pk=pk).notifier,
                reference='{}:{}'.format(
                    ref_type,
                    to_global_id('{}Node'.format(ref_type), root.pk),
                ),
                description=description,
                subject=entry,
            )

    elif action == 'post_remove':
        for pk in pk_set:
            models.MentionNotification.objects.filter(
                notifier=ibis.models.User.objects.get(pk=pk).notifier,
                subject=entry,
            ).delete()
