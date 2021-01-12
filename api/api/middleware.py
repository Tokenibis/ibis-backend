from django.contrib.auth import login
from django.conf import settings

import ibis.models


def AuthenticateAllMiddleware(get_response):
    def middleware(request):
        if ibis.models.User.objects.filter(username=settings.AUTHENTICATE_AS):
            user = ibis.models.User.objects.get(
                username=settings.AUTHENTICATE_AS)
        elif settings.AUTHENTICATE_AS == '__person__':
            user = ibis.models.Person.objects.last()
        elif settings.AUTHENTICATE_AS == '__organization__':
            user = ibis.models.Organization.objects.last()
        elif settings.AUTHENTICATE_AS == '__bot__':
            user = ibis.models.Bot.objects.last()
        else:
            raise ValueError('Unknown test authentication type')

        login(request, user)
        return get_response(request)

    return middleware
