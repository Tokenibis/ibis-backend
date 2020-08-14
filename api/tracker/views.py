import tracker.models as models

from django.utils.timezone import localtime
from rest_framework import generics, response
from hashlib import sha256


class WaitView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        log = models.Log.objects.filter(
            mutation=True).order_by('-created').first()
        return response.Response({
            'state':
            sha256(str(log if log else '').encode('utf-8')).hexdigest(),
            'time':
            log.created if log else '',
        })
