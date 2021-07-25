import ibis.models
import distribution.models as models

from django.db.models.signals import post_save
from django.dispatch import receiver
from api.management.commands.loaddata import STATE


@receiver(post_save, sender=ibis.models.Person)
def handlePersonCreate(sender, instance, created, raw, **kwargs):
    if STATE['LOADING_DATA'] or not created:
        return

    instance.distributor.distribute_initial_safe()
