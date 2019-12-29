from django.contrib.auth import login

import ibis.models


def AuthenticateAllMiddleware(get_response):
    def middleware(request):
        user = ibis.models.Person.objects.all().first()
        login(request, user)
        return get_response(request)

    return middleware
