from datetime import datetime

from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager


class ProfileManager(UserManager):
    pass


class Profile(AbstractUser):
    objects = ProfileManager()
    nickname = models.CharField(max_length=32)
    create_time = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return '{}({})'.format(self.nickname, self.id)
