import ibis.models
import notifications.models as models

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from graphql_relay.node.node import to_global_id


@receiver(post_save, sender=ibis.models.Deposit)
def handleDepositCreate(sender, instance, created, **kwargs):
    if not created:
        return

    if ibis.models.DepositCategory.objects.filter(title='ubp').exists(
    ) and instance.category == ibis.models.DepositCategory.objects.get(
            title='ubp'):
        description = 'You have a fresh ${:.2f} waiting for you'.format(
            instance.amount / 100)

        models.UbpNotification.objects.create(
            notifier=instance.user.notifier,
            reference='{}:{}'.format(
                ibis.models.Deposit.__name__,
                to_global_id('DepositNode', instance.pk),
            ),
            description=description,
            subject=instance,
            created=instance.created,
        )

    else:
        description = 'Your deposit of ${:.2f} was successful'.format(
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


@receiver(post_save, sender=ibis.models.Donation)
def handleDonationCreate(sender, instance, created, **kwargs):
    if not created:
        return

    entry = ibis.models.Entry.objects.get(pk=instance.pk)

    reference = '{}:{}'.format(
        ibis.models.Donation.__name__,
        to_global_id('DonationNode', instance.pk),
    )

    models.DonationNotification.objects.create(
        notifier=instance.target.notifier,
        reference=reference,
        description='{} donated ${:.2f}'.format(
            str(entry.user),
            instance.amount / 100,
        ),
        subject=instance,
        created=instance.created,
    )


@receiver(post_save, sender=ibis.models.Transaction)
def handleTransactionCreate(sender, instance, created, **kwargs):
    if not created:
        return

    entry = ibis.models.Entry.objects.get(pk=instance.pk)

    reference = '{}:{}'.format(
        ibis.models.Transaction.__name__,
        to_global_id('TransactionNode', instance.pk),
    )

    models.TransactionNotification.objects.create(
        notifier=instance.target.notifier,
        reference=reference,
        description='{} sent you ${:.2f}'.format(
            str(entry.user),
            instance.amount / 100,
        ),
        subject=instance,
        created=instance.created,
    )


@receiver(post_save, sender=ibis.models.News)
def handleNewsCreate(sender, instance, created, **kwargs):
    if not created:
        return

    entry = ibis.models.Entry.objects.get(pk=instance.pk)

    reference = '{}:{}'.format(
        ibis.models.News.__name__,
        to_global_id('NewsNode', instance.pk),
    )

    for target in entry.user.follower.all():
        models.NewsNotification.objects.create(
            notifier=target.ibisuser.notifier,
            reference=reference,
            description='{} released a news story'.format(str(entry.user)),
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Event)
def handleEventCreate(sender, instance, created, **kwargs):
    if not created:
        return

    entry = ibis.models.Entry.objects.get(pk=instance.pk)

    reference = '{}:{}'.format(
        ibis.models.Event.__name__,
        to_global_id('EventNode', instance.pk),
    )

    for target in entry.user.follower.all():
        models.EventNotification.objects.create(
            notifier=target.ibisuser.notifier,
            reference=reference,
            description='{} planned an new event'.format(str(entry.user)),
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Post)
def handlePostCreate(sender, instance, created, **kwargs):
    if not created:
        return

    entry = ibis.models.Entry.objects.get(pk=instance.pk)

    reference = '{}:{}'.format(
        ibis.models.Post.__name__,
        to_global_id('PostNode', instance.pk),
    )

    for target in entry.user.follower.all():
        notifier = target.ibisuser.notifier
        models.PostNotification.objects.create(
            notifier=notifier,
            reference=reference,
            description='{} made a new post'.format(str(entry.user)),
            subject=instance,
            created=instance.created,
        )


@receiver(post_save, sender=ibis.models.Comment)
def handleCommentCreate(sender, instance, created, **kwargs):
    if not created:
        return

    entry = ibis.models.Entry.objects.get(pk=instance.pk)
    current = instance

    notification_info = []

    while hasattr(current, 'comment'):
        parent = current.comment.parent
        notifiers = [parent.user.ibisuser.notifier]
        if models.get_submodel(
                parent,
                ibis.models.Entry,
        ) == ibis.models.Donation:
            notifiers.append(parent.donation.target.ibisuser.notifier)
        if models.get_submodel(
                parent,
                ibis.models.Entry,
        ) == ibis.models.Transaction:
            notifiers.append(parent.transaction.target.ibisuser.notifier)

        for notifier in notifiers:
            if notifier not in [x['notifier'] for x in notification_info
                                ] and notifier != entry.user.notifier:
                description = '{} replied to your {}'.format(
                    str(entry.user),
                    models.get_submodel(
                        parent,
                        ibis.models.Entry,
                    ).__name__.lower(),
                )
                notification_info.append({
                    'notifier': notifier,
                    'description': description,
                    'subject': instance,
                })

        current = parent

    ref_type = models.get_submodel(current, ibis.models.Entry).__name__
    ref_id = to_global_id('{}Node'.format(ref_type), current.pk)
    reference = '{}:{}'.format(ref_type, ref_id)

    if notification_info:
        notification_info[-1]['description'] = '{} replied to your {}'.format(
            str(entry.user), ref_type.lower())

    for info in notification_info:
        models.CommentNotification.objects.create(
            notifier=info['notifier'],
            reference=reference,
            description=info['description'],
            subject=info['subject'],
            created=instance.created,
        )


@receiver(m2m_changed, sender=ibis.models.IbisUser.following.through)
def handleFollowUpdate(sender, instance, action, pk_set, **kwargs):
    user = ibis.models.IbisUser.objects.get(pk=instance.pk)
    if action == 'post_add':
        for pk in pk_set:
            target = ibis.models.IbisUser.objects.get(pk=pk)
            notifier = target.notifier

            ref_type = models.get_submodel(
                user,
                ibis.models.IbisUser,
            ).__name__

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
                notifier=ibis.models.IbisUser.objects.get(pk=pk).notifier,
                subject=user,
            ).delete()


@receiver(m2m_changed, sender=ibis.models.Entry.like.through)
def handleLikeUpdate(sender, instance, action, pk_set, **kwargs):
    entry = ibis.models.Entry.objects.get(pk=instance.pk)
    if action == 'post_add':
        for pk in pk_set:
            user = ibis.models.IbisUser.objects.get(pk=pk)
            notifier = entry.user.notifier
            description = '{} liked your {}'.format(
                str(user),
                models.get_submodel(
                    entry,
                    ibis.models.Entry,
                ).__name__,
            )

            root = entry
            while models.get_submodel(
                    root,
                    ibis.models.Entry,
            ) == ibis.models.Comment:
                root = root.comment.parent

            ref_type = models.get_submodel(
                root,
                ibis.models.Entry,
            ).__name__

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
            models.LikeNotification.objects.filter(
                notifier=entry.user.notifier,
                subject=entry,
                user=ibis.models.IbisUser.objects.get(pk=pk),
            ).delete()


@receiver(m2m_changed, sender=ibis.models.Entry.mention.through)
def handleMentionUpdate(sender, instance, action, pk_set, **kwargs):
    entry = ibis.models.Entry.objects.get(pk=instance.pk)
    if action == 'post_add':
        for pk in pk_set:
            description = '{} mentioned you in a {}'.format(
                entry.user,
                models.get_submodel(entry, ibis.models.Entry).__name__.lower(),
            )

            root = entry
            while models.get_submodel(
                    root,
                    ibis.models.Entry,
            ) == ibis.models.Comment:
                root = root.comment.parent

            ref_type = models.get_submodel(
                root,
                ibis.models.Entry,
            ).__name__

            models.MentionNotification.objects.create(
                notifier=ibis.models.IbisUser.objects.get(pk=pk).notifier,
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
                notifier=ibis.models.IbisUser.objects.get(pk=pk).notifier,
                subject=entry,
            ).delete()
