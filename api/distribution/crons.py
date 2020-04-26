# upon startup: check through to make sure we've distributed
# everything that should be distributed. distribute it if not.
# Otherwise, wait until midnight on Thursday night

from django.utils.timezone import now, localtime
from django_cron import CronJobBase, Schedule

import distribution.models as models

FREQUENCY = 10

STATE = {
    'UPCOMING':
    localtime(now()).replace(
        year=2019,
        month=4,
        day=5,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ),
}


class DistributionCron(CronJobBase):
    schedule = Schedule(run_every_mins=FREQUENCY)
    code = 'distribution.distribution_cron'

    def do(self):
        if STATE['UPCOMING'] < localtime(now()):
            STATE['UPCOMING'] = models.Distributor.distribute_all_safe()
