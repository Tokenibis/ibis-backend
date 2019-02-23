"""
Definitions for Django models for Ibis profiles
"""

from django.contrib.auth.models import AbstractUser, UserManager


class ProfileManager(UserManager):
    pass


class Profile(AbstractUser):
    objects = ProfileManager()

    def __str__(self):
        return self.username
