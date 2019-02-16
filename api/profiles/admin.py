from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Profile


class ProfileAdmin(UserAdmin):
    model = Profile


admin.site.register(Profile, ProfileAdmin)
