import random

from gifts.models import initiate_gift
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Consider sending a gift'

    def handle(self, *args, **options):

        if random.random() < settings.GIFT_PROBABILITY_HOURLY:
            initiate_gift()
