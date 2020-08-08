from django.db.models.signals import post_save
from django.conf import settings

import ibis.models as models


def scoreFundraisedDescending(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    organizations = list(
        models.Organization.objects.exclude(username=settings.IBIS_USERNAME_ROOT))
    organizations.sort(key=lambda x: x.fundraised(), reverse=True)
    for i, organization in enumerate(organizations):
        if organization.score != i + 1:
            organization.score = i + 1
            organization.save()


score_organization = {
    'fundraised_descending': scoreFundraisedDescending,
}

if settings.SIGNAL_SCORE_ORGANIZATION:
    post_save.connect(
        score_organization[settings.SIGNAL_SCORE_ORGANIZATION],
        sender=models.Donation,
    )
