from datetime import datetime

from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils import timezone


class ProfileManager(UserManager):
    pass


class Profile(AbstractUser):
    objects = ProfileManager()
    nickname = models.CharField(max_length=32)

    # populate create_time with current timezone-aware datetime
    create_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return '{}({})'.format(self.nickname, self.id)
