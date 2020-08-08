import json
import ibis.models as models

from django.conf import settings
from django.http.request import RawPostDataException
from graphql import GraphQLError
from graphql.language.base import parse


def BotGasMiddleware(get_response):
    def middleware(request):
        if not models.Bot.objects.filter(id=request.user.id).exists():
            return get_response(request)

        bot = models.Bot.objects.get(id=request.user.id)

        if bot.gas < 0:
            if bot.balance() >= bot.tank / settings.BOT_GAS_PRICE:
                models.Donation.create(
                    user=bot,
                    target=models.Organization.objects.get(
                        username=settings.ROOT_ORGANIZATION_USERNAME),
                    amount=bot.tank / settings.GAS_PRICE,
                )
            else:
                raise GraphQLError('Bot has no money left for gas')

        response = get_response(request)

        if request.method == 'POST' and 'graphql' in request.path:
            try:
                body = json.loads(request.body.decode())
                definition = parse(body['query']).definitions[0]
            except RawPostDataException:
                return response

            if definition.operation == 'query':
                bot.gas -= settings.BOT_GAS_QUERY_FIXED + \
                    settings.BOT_GAS_QUERY_VARIABLE * len(response.content)
            elif response.status_code == 200:
                # only charge if successful
                try:
                    bot.gas -= settings.BOT_GAS_MUTATION[
                        definition.selection_set.selections[0].name.value]
                except KeyError:
                    bot.gas -= max(settings.BOT_GAS_MUTATION.values())
            bot.save()

        return response

    return middleware
