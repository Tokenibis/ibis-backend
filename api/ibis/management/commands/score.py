import ibis.models as models

from django.conf import settings
from django.utils.timezone import localtime, timedelta
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Update scores'

    def handle(self, *args, **options):
        time = localtime()

        def _score(org):
            return (
                org.date_joined > time -
                timedelta(days=7 * settings.SORT_ORGANIZATION_WINDOW_JOINED),
                org.has_recent_entry(),
                org.recent_response_rate(),
                hash(str(org.fundraised_recently()) + str(org.id)),
            )

        for i, x in enumerate(
                sorted(
                    models.Organization.objects.filter(is_active=True).exclude(
                        username=settings.IBIS_USERNAME_ROOT),
                    key=_score,
                )):
            x.score = i
            x.save()
