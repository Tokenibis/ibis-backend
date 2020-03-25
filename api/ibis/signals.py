import random

from hashlib import sha256
from django.db.models.signals import post_save
from django.conf import settings

import ibis.models as models

INITIAL_UBP_DEFAULT = 1000


def scoreFundraisedDescending(sender, instance, created, **kwargs):
    if not created:
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


def createPersonInitialUbp(sender, instance, created, raw, **kwargs):
    if raw or not created:
        return

    try:
        amount = settings.SIGNAL_CREATE_PERSON_INITIAL_UBP
    except AttributeError:
        amount = INITIAL_UBP_DEFAULT
    assert amount > 0, 'Initial UBP is non-positive'

    models.Deposit.objects.create(
        user=instance.ibisuser_ptr,
        amount=amount,
        payment_id='ubp:{}'.format(
            sha256(str(random.random()).encode('utf-8')).hexdigest(), ),
    )


create_person = {
    'initial_ubp': createPersonInitialUbp,
}

if settings.SIGNAL_CREATE_PERSON:
    post_save.connect(
        create_person[settings.SIGNAL_CREATE_PERSON],
        sender=models.Person,
    )
