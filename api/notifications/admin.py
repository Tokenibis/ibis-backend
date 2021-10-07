from django.contrib import admin

import notifications.models as models


@admin.register(models.Email)
class EmailAdmin(admin.ModelAdmin):
    raw_id_fields = ['notification']


admin.site.register(models.Notifier)
admin.site.register(models.Notification)
