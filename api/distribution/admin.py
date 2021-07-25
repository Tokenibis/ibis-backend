from django.contrib import admin

import distribution.models as models


class GoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'created')


admin.site.register(models.Goal, GoalAdmin)
admin.site.register(models.Investment)
admin.site.register(models.Distributor)
