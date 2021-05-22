import os
import json
import ibis.models
import tracker.models as models

from django.http.request import RawPostDataException

DIR = os.path.dirname(os.path.realpath(__file__))

IGNORE = {
    'MessageDirectList',
    'MessageChannelList',
    'Notifier',
    'NotifierUpdate',
}


def TrackerMiddleware(get_response):
    def middleware(request):
        response = get_response(request)

        try:
            if request.method == 'POST' and 'graphql' in request.path:
                body = json.loads(request.body.decode())

                if 'operationName' in body and body[
                        'operationName'] not in IGNORE:
                    log = models.Log.objects.create(
                        user=ibis.models.User.objects.get(pk=request.user.id),
                        graphql_operation=body['operationName'],
                        response_code=response.status_code,
                    )
                    if 'variables' in body:
                        log.graphql_variables = body['variables']
                    if 'query' in body:
                        log.mutation = body['query'].startswith('mutation')
                    if hasattr(request, 'headers'):
                        if 'User-Agent' in request.headers:
                            log.user_agent = request.headers['User-Agent']
                        if 'Pwa-Standalone' in request.headers:
                            log.pwa_standalone = True if request.headers[
                                'Pwa-Standalone'] == 'true' else False

                    log.save()
        except ibis.models.User.DoesNotExist:
            pass
        except RawPostDataException:
            pass

        return response

    return middleware
