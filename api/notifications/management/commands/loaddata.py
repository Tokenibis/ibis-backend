"""
Additional treatment for the loaddata command.
Location example: project/app/management/commands/loaddata.py
"""
from django.core.management.commands import loaddata

# Really ugly hack because Django doesn't provide 'raw' field for
# m2m_changed signals.
STATE = {}


class Command(loaddata.Command):

    # override loaddata so that it never schedules emails to go out
    def handle(self, *args, **options):
        STATE['LOADING_DATA'] = True
        super(Command, self).handle(*args, **options)
        STATE['LOADING_DATA'] = False
