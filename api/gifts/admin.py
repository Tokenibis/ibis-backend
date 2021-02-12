from django.contrib import admin
import gifts.models as models

# Register your models here.
admin.site.register(models.GiftType)
admin.site.register(models.Gift)
