from django.db.models.signals import post_save
from django.conf import settings

import ibis.models as models


def scoreFundraisedDescending(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    nonprofits = list(models.Nonprofit.objects.all())
    nonprofits.sort(key=lambda x: x.fundraised(), reverse=True)
    for i, nonprofit in enumerate(nonprofits):
        if settings.SIGNAL_SCORE_NONPROFIT_IGNORE and \
           nonprofit.username in settings.SIGNAL_SCORE_NONPROFIT_IGNORE:
            continue

        if nonprofit.score != i + len(settings.SIGNAL_SCORE_NONPROFIT_IGNORE):
            nonprofit.score = i + len(settings.SIGNAL_SCORE_NONPROFIT_IGNORE)
            nonprofit.save()


score_nonprofit = {
    'fundraised_descending': scoreFundraisedDescending,
}

if settings.SIGNAL_SCORE_NONPROFIT:
    post_save.connect(
        score_nonprofit[settings.SIGNAL_SCORE_NONPROFIT],
        sender=models.Donation,
    )
