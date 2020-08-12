from django.contrib.auth import login
from django.conf import settings

import ibis.models


def AuthenticateAllMiddleware(get_response):
    def middleware(request):
        if settings.AUTHENTICATE_AS == 'person':
            user = ibis.models.Person.objects.last()
        elif settings.AUTHENTICATE_AS == 'organization':
            user = ibis.models.Organization.objects.last()
        elif settings.AUTHENTICATE_AS == 'bot':
            user = ibis.models.Bot.objects.last()
        else:
            raise ValueError('Unknown test authentication type')

        login(request, user)
        return get_response(request)

    return middleware
