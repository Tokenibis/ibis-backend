# import code
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
            if 'USERNAME' in request.environ:
                log.environ_username = request.environ['USERNAME']
            if 'HTTP_USER_AGENT' in request.environ:
                log.environ_useragent = request.environ['HTTP_USER_AGENT']
            log.response_code = response.status_code
            log.save()

            # code.interact(local=locals())

        return response

    return middleware
