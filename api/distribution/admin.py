from django.contrib import admin

import distribution.models as models


class GoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'created')


@admin.register(models.Investment)
class InvestmentAdmin(admin.ModelAdmin):
    raw_id_fields = ['deposit']


admin.site.register(models.Goal, GoalAdmin)
admin.site.register(models.Distributor)
