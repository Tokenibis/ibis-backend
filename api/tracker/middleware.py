import json
import tracker.models as models
from users.models import User


def TrackerMiddleware(get_response):
    def middleware(request):
        response = get_response(request)

        if request.method == 'POST' and 'graphql' in request.path:
            body = json.loads(request.body.decode())
            log = models.Log.objects.create()

            try:
                log.user = User.objects.get(pk=request.user.id)
            except User.DoesNotExist:
                pass

            if 'operationName' in body:
                log.graphql_operation = body['operationName']
            if 'variables' in body:
                log.graphql_variables = body['variables']
            if 'User-Agent' in request.headers:
                log.user_agent = request.headers['User-Agent']
            if 'Pwa-Standalone' in request.headers:
                log.pwa_standalone = True if request.headers[
                    'Pwa-Standalone'] == 'true' else False

            log.response_code = response.status_code
            log.save()

        return response

    return middleware
