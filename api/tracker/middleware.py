import json
import ibis.models
import tracker.models as models

from django.http.request import RawPostDataException


def TrackerMiddleware(get_response):
    def middleware(request):
        response = get_response(request)

        try:
            if request.method == 'POST' and 'graphql' in request.path:
                body = json.loads(request.body.decode())
                log = models.Log.objects.create()
                log.user = ibis.models.IbisUser.objects.get(pk=request.user.id)

                if 'operationName' in body:
                    log.graphql_operation = body['operationName']
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

                    log.response_code = response.status_code
                log.save()
        except ibis.models.IbisUser.DoesNotExist:
            pass
        except RawPostDataException:
            pass

        return response

    return middleware
