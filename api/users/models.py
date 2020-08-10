"""
Definitions for Django models for Ibis users
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, UserManager


class GeneralUser(AbstractUser):
    objects = UserManager()

    first_name = models.CharField(_('first name'), max_length=150, blank=True)
