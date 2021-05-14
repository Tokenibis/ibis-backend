from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialToken

admin.site.unregister(Site)
admin.site.unregister(Group)
admin.site.unregister(Token)
admin.site.unregister(EmailAddress)
admin.site.unregister(SocialToken)
