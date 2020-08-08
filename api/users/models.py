"""
Definitions for Django models for Ibis users
"""

from django.contrib.auth.models import AbstractUser, UserManager


class GeneralUser(AbstractUser):
    objects = UserManager()
