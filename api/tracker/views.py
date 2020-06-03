import tracker.models as models

from rest_framework import generics, response
from hashlib import sha256


class WaitView(generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        log = models.Log.objects.filter(mutation=True).last()
        return response.Response({
            'state':
            sha256(str(log).encode('utf-8')).hexdigest(),
            'time':
            log.created,
        })
