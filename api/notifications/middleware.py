import json
from django.utils.timezone import now
from graphql_relay.node.node import from_global_id, to_global_id
from notifications.models import Notification, Email
from django.core.exceptions import ObjectDoesNotExist

import ibis.models as ibis


def handleFollowCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
        notifier = ibis.Person.objects.get(
            pk=from_global_id(variables['target'])[1]).notifier
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    description = '{} started following you'.format(str(user))

    notification = Notification.objects.create(
        notifier=notifier,
        category=Notification.RECEIVED_FOLLOW,
        reference='{}:{}'.format(
            ibis.Person.__name__,
            variables['user'],
        ),
        deduper='follow:{}:{}'.format(variables['user'], variables['target']),
        description=description,
    )
    notification.save()

    if notifier.email_follow:
        email = Email.objects.create(
            notification=notification,
            subject=description,
            body='TODO',
            schedule=now(),
        )
        email.save()

    Notification.objects.filter(deduper=notification.deduper).exclude(
        pk=notification.id).delete()


def handleLikeCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
        current = ibis.Entry.objects.get(
            pk=from_global_id(variables['target'])[1])
        notifier = current.user.person.notifier
    except (ObjectDoesNotExist, AttributeError):
        # target of like is probably a nonprofit; just drop silently
        return

    while hasattr(current, 'comment'):
        current = current.comment.parent

    for Subclass in ibis.Entry.__subclasses__():
        if Subclass.objects.filter(pk=current.id).exists():
            ref_type = Subclass.__name__
            ref_id = to_global_id('{}Node'.format(ref_type), current.id)
            break

    description = '{} liked your {}'.format(str(user), ref_type.lower())

    notification = Notification.objects.create(
        notifier=notifier,
        category=Notification.RECEIVED_LIKE,
        reference='{}:{}'.format(ref_type, ref_id),
        deduper='like:{}:{}'.format(variables['user'], variables['target']),
        description=description,
    )
    notification.save()

    if notifier.email_like:
        email = Email.objects.create(
            notification=notification,
            subject=description,
            body='TODO',
            schedule=now(),
        )
        email.save()

    Notification.objects.filter(deduper=notification.deduper).exclude(
        pk=notification.id).delete()


def handleTransactionCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
        notifier = ibis.Person.objects.get(
            pk=from_global_id(variables['target'])[1]).notifier
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    description = '{} sent you ${:.2f}'.format(
        str(user),
        variables['amount'] / 100,
    )

    notification = Notification.objects.create(
        notifier=notifier,
        category=Notification.RECEIVED_TRANSACTION,
        reference='{}:{}'.format(
            ibis.Transaction.__name__,
            data['createTransaction']['transaction']['id'],
        ),
        deduper='transaction:{}'.format(
            data['createTransaction']['transaction']['id']),
        description=description,
    )
    notification.save()

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


def handleCommentCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
        current = ibis.Comment.objects.get(
            pk=from_global_id(data['createComment']['comment']['id'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    description = '{} replied to your comment'.format(str(user))

    notifications = []

    while hasattr(current, 'comment'):
        parent = current.comment.parent
        if hasattr(parent.user, 'person'):
            notifier = parent.user.person.notifier
            if notifier not in [x.notifier for x in notifications]:
                notification = Notification.objects.create(
                    notifier=notifier,
                    category=Notification.RECEIVED_COMMENT,
                    deduper='comment:{}:{}'.format(
                        data['createComment']['comment']['id'],
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

    for Subclass in ibis.Entry.__subclasses__():
        if Subclass.objects.filter(pk=current.id).exists():
            ref_type = Subclass.__name__
            ref_id = to_global_id('{}Node'.format(ref_type), current.id)
            break

    notifications[-1].description = '{} replied to your {}'.format(
        str(user), ref_type.lower())

    for notification in notifications:
        notification.reference = '{}:{}'.format(ref_type, ref_id)
        notification.save()

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


def handleNewsCreate(variables, data):
    try:
        user = ibis.Nonprofit.objects.get(
            pk=from_global_id(variables['user'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    for target in user.follower.all():
        try:
            notifier = target.person.notifier
        except ObjectDoesNotExist:
            print('ERROR: notification received a bad input')
            continue

        description = '{} released a news story'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_NEWS,
            reference='{}:{}'.format(
                ibis.News.__name__,
                data['createNews']['news']['id'],
            ),
            deduper='news:{}:{}'.format(
                data['createNews']['news']['id'],
                to_global_id('PersonNode', target.id),
            ),
            description=description,
        )

        notification.save()

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


def handleEventCreate(variables, data):
    try:
        user = ibis.Nonprofit.objects.get(
            pk=from_global_id(variables['user'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    for target in user.follower.all():
        try:
            notifier = target.person.notifier
        except ObjectDoesNotExist:
            print('ERROR: notification received a bad input')
            continue

        description = '{} planned an new event'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_EVENT,
            reference='{}:{}'.format(
                ibis.Event.__name__,
                data['createEvent']['event']['id'],
            ),
            deduper='event:{}:{}'.format(
                data['createEvent']['event']['id'],
                to_global_id('PersonNode', target.id),
            ),
            description=description,
        )

        notification.save()

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


def handlePostCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    for target in user.follower.all():
        try:
            notifier = target.person.notifier
        except ObjectDoesNotExist:
            print('ERROR: notification received a bad input')
            continue

        description = '{} made a new post'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_POST,
            reference='{}:{}'.format(
                ibis.Post.__name__,
                data['createPost']['post']['id'],
            ),
            deduper='post:{}:{}'.format(
                data['createPost']['post']['id'],
                to_global_id('PersonNode', target.id),
            ),
            description=description,
        )

        notification.save()

        Notification.objects.filter(deduper=notification.deduper).exclude(
            pk=notification.id).delete()


def handleFollowDelete(variables, data):
    Notification.objects.filter(deduper='follow:{}:{}'.format(
        variables['user'], variables['target'])).delete()


def handleLikeDelete(variables, data):
    Notification.objects.filter(deduper='like:{}:{}'.format(
        variables['user'], variables['target'])).delete()


def handleTransactionDelete(variables, data):
    Notification.objects.filter(
        deduper='transaction:{}'.format(variables['id'])).delete()


def handleCommentDelete(variables, data):
    Notification.objects.filter(
        deduper__startswith='comment:{}:'.format(variables['id'])).delete()


def handleNewsDelete(variables, data):
    Notification.objects.filter(
        deduper__startswith='news:{}:'.format(variables['id'])).delete()


def handleEventDelete(variables, data):
    Notification.objects.filter(
        deduper__startswith='event:{}:'.format(variables['id'])).delete()


def handlePostDelete(variables, data):
    Notification.objects.filter(
        deduper__startswith='post:{}:'.format(variables['id'])).delete()


switcher = {
    'FollowCreate': handleFollowCreate,
    'LikeCreate': handleLikeCreate,
    'TransactionCreate': handleTransactionCreate,
    'CommentCreate': handleCommentCreate,
    'NewsCreate': handleNewsCreate,
    'EventCreate': handleEventCreate,
    'PostCreate': handlePostCreate,
    'FollowDelete': handleFollowDelete,
    'LikeDelete': handleLikeDelete,
    'TransactionDelete': handleTransactionDelete,
    'CommentDelete': handleCommentDelete,
    'NewsDelete': handleNewsDelete,
    'EventDelete': handleEventDelete,
    'PostDelete': handlePostDelete,
}


def NotificationMiddleware(get_response):
    def middleware(request):
        response = get_response(request)

        if request.method == 'POST' and 'graphql' in request.path:
            request_content = json.loads(request.body.decode())
            response_content = json.loads(response.content.decode())

            if response.status_code == 200 and \
               'operationName' in request_content and \
               'errors' not in response_content and \
               request_content['operationName'] in switcher:
                switcher[request_content['operationName']](
                    request_content['variables'],
                    response_content['data'],
                )

        return response

    return middleware
