import ibis.models as models

from django.utils.timezone import localtime, timedelta
from django.db.models.signals import post_save, m2m_changed
from django.conf import settings
from api.management.commands.loaddata import STATE


def score_organizations(sender, instance, **kwargs):
    # don't call when loading fixtures
    if STATE['LOADING_DATA']:
        return

    # make sure this isn't just an object update
    if 'created' in kwargs and not kwargs['created']:
        return

    # if comment, make sure this is an org comment on a donation
    if isinstance(
            instance,
            models.Comment,
    ) and not (models.Donation.objects.filter(pk=instance.parent.pk).exists()
               and models.Organization.objects.filter(
                   pk=instance.user.pk).exists()):
        return

    # if like, make sure this is an org like on a donation
    if 'pk_set' in kwargs and not (models.Donation.objects.filter(
            pk=instance.pk)).exists() and any(
                models.Organization.objects.filter(pk=x)
                for x in kwargs['pk_set']):
        return

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


for x in [
        models.Organization,
        models.Donation,
        models.News,
        models.Event,
        models.Comment,
]:
    post_save.connect(score_organizations, sender=x)

m2m_changed.connect(score_organizations, sender=models.Entry.like.through)
