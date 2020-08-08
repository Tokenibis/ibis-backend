"""
Updates for the Django admin panel for Ibis users
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import GeneralUser

admin.site.register(GeneralUser, UserAdmin)
