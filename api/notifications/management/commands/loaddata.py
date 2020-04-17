"""
Additional treatment for the loaddata command.
Location example: project/app/management/commands/loaddata.py
"""
import notifications.models as models
from django.core.management.commands import loaddata


class Command(loaddata.Command):

    # override loaddata so that it never schedules emails to go out
    def handle(self, *args, **options):
        original = models.Email.objects.all()
        super(Command, self).handle(*args, **options)
        models.Email.objects.all().exclude(id__in=original).delete()
