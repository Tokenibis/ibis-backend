import json
from datetime import datetime
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
        description=description,
    )
    notification.save()

    if notifier.email_follow:
        email = Email.objects.create(
            notification=notification,
            subject=description,
            body='TODO',
            schedule=datetime.now(),
        )
        email.save()


def handleTransactionCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
        notifier = ibis.Entry.objects.get(
            pk=from_global_id(variables['target'])[1]).user.person.notifier
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    description = '{} sent you ${:.2f}'.format(
        str(user),
        variables['amount'] / 100,
    )

    print(data)
    notification = Notification.objects.create(
        notifier=notifier,
        category=Notification.RECEIVED_TRANSACTION,
        reference='{}:{}'.format(
            ibis.Transaction.__name__,
            data['createTransaction']['transaction']['id'],
        ),
        description=description,
    )
    notification.save()

    if notifier.email_transaction:
        email = Email.objects.create(
            notification=notification,
            subject=description,
            body='TODO',
            schedule=datetime.now(),
        )
        email.save()


def handleCommentCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
        current = ibis.Comment.objects.get(
            pk=from_global_id(data['createComment']['comment']['id'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    description = '{} commented on your activity'.format(str(user))

    notifications = []

    while hasattr(current, 'comment'):
        parent = current.comment.parent
        if hasattr(parent.user, 'person'):
            notifier = parent.user.person.notifier
            if notifier not in [x.notifier for x in notifications]:
                notification = Notification.objects.create(
                    notifier=notifier,
                    category=Notification.RECEIVED_COMMENT,
                    description=description,
                )
                notifications.append(notification)
                if notifier.email_comment:
                    email = Email.objects.create(
                        notification=notification,
                        subject=description,
                        body='TODO',
                        schedule=datetime.now(),
                    )
                    email.save()
        current = parent

    for Subclass in ibis.Entry.__subclasses__():
        if Subclass.objects.filter(pk=current.id).exists():
            print(Subclass.__name__)
            print(current.id)
            ref_type = Subclass.__name__
            ref_id = to_global_id('{}Node'.format(ref_type), parent.id)
            break

    for notification in notifications:
        notification.reference = '{}:{}'.format(ref_type, ref_id)
        notification.save()


def handleLikeCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
        notifier = ibis.Entry.objects.get(
            pk=from_global_id(variables['target'])[1]).user.person.notifier
    except (ObjectDoesNotExist, AttributeError):
        # target of like is probably a nonprofit; just drop silently
        return

    description = '{} liked your activity'.format(str(user))

    notification = Notification.objects.create(
        notifier=notifier,
        category=Notification.RECEIVED_LIKE,
        reference='{}:{}'.format(
            ibis.Person.__name__,
            variables['target'],
        ),
        description=description,
    )
    notification.save()

    if notifier.email_like:
        email = Email.objects.create(
            notification=notification,
            subject=description,
            body='TODO',
            schedule=datetime.now(),
        )
        email.save()


def handleNewsCreate(variables, data):
    try:
        user = ibis.Nonprofit.objects.get(
            pk=from_global_id(variables['user'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    for target in user.followers:
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
            description=description,
        )

        notification.save()


def handleEventCreate(variables, data):
    try:
        user = ibis.Nonprofit.objects.get(pk=from_global_id(variables['user'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    for target in user.followers:
        try:
            notifier = target.person.notifier
        except ObjectDoesNotExist:
            print('ERROR: notification received a bad input')
            continue

        description = '{} planned an event'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_EVENT,
            reference='{}:{}'.format(
                ibis.Event.__name__,
                data['createEvent']['event']['id'],
            ),
            description=description,
        )

        notification.save()


def handlePostCreate(variables, data):
    try:
        user = ibis.Person.objects.get(pk=from_global_id(variables['user'])[1])
    except ObjectDoesNotExist:
        print('ERROR: notification received a bad input')
        return

    for target in user.followers:
        try:
            notifier = target.person.notifier
        except ObjectDoesNotExist:
            print('ERROR: notification received a bad input')
            continue

        description = '{} made a post'.format(str(user))

        notification = Notification.objects.create(
            notifier=notifier,
            category=Notification.FOLLOWING_POST,
            reference='{}:{}'.format(
                ibis.Post.__name__,
                data['createPost']['post']['id'],
            ),
            description=description,
        )

        notification.save()


switcher = {
    'FollowCreate': handleFollowCreate,
    'TransactionCreate': handleTransactionCreate,
    'CommentCreate': handleCommentCreate,
    'LikeCreate': handleLikeCreate,
    'NewsCreate': handleNewsCreate,
    'EventCreate': handleEventCreate,
    'PostCreate': handlePostCreate,
}


def NotificationMiddleware(get_response):
    def middleware(request):
        response = get_response(request)

        if request.method == 'POST' and 'graphql' in request.path:
            request_content = json.loads(request.body.decode())
            response_content = json.loads(response.content.decode())

            if 'operationName' in request_content and \
               request_content['operationName'] in switcher and \
               response.status_code == 200:
                switcher[request_content['operationName']](
                    request_content['variables'],
                    response_content['data'],
                )

        return response

    return middleware
