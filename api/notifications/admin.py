from django.contrib import admin

import notifications.models as models

admin.site.register(models.Notifier)
admin.site.register(models.Notification)
admin.site.register(models.Email)
