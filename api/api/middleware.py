from django.contrib.auth import login
from django.conf import settings

import ibis.models


def AuthenticateAllMiddleware(get_response):
    def middleware(request):
        if settings.AUTHENTICATE_AS == 'person':
            user = ibis.models.Person.objects.all().first()
        elif settings.AUTHENTICATE_AS == 'organization':
            user = ibis.models.Organization.objects.all().first()
        else:
            raise ValueError('Unknown test authentication type')

        login(request, user)
        return get_response(request)

    return middleware
