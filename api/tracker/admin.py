from django.contrib import admin

import tracker.models as models


class LogAdmin(admin.ModelAdmin):
    readonly_fields = ('created', )


admin.site.register(models.Log, LogAdmin)
