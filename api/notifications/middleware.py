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
        # target of follow is probably a nonprofit; just drop silently
        return

    description = '{} started following you'.format(str(user))

    notification = Notification.objects.create(
        notifier=notifier,
        category=Notification.RECEIVED_FOLLOW,
        reference='{}:{}'.format(
            ibis.Person.__name__,
            variables['user'],
        ),
        deduper='follow:{}:{}'.format(
            from_global_id(variables['user'])[1],
            from_global_id(variables['target'])[1],
        ),
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
        deduper='like:{}:{}'.format(
            from_global_id(variables['user'])[1],
            from_global_id(variables['target'])[1],
        ),
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


def handleFollowDelete(variables, data):
    Notification.objects.filter(
        deduper='follow:{}:{}'.format(
            from_global_id(variables['user'])[1],
            from_global_id(variables['target'])[1],
        ),
    ).delete()


def handleLikeDelete(variables, data):
    Notification.objects.filter(
        deduper='like:{}:{}'.format(
            from_global_id(variables['user'])[1],
            from_global_id(variables['target'])[1],
        ),
    ).delete()


switcher = {
    'FollowCreate': handleFollowCreate,
    'LikeCreate': handleLikeCreate,
    'FollowDelete': handleFollowDelete,
    'LikeDelete': handleLikeDelete,
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
