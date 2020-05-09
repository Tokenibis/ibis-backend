from django.contrib import admin

import ibis.models as models


@admin.register(models.Nonprofit)
class NonprofitAdmin(admin.ModelAdmin):
    readonly_fields = ('balance_str', 'fundraised_str')

    def balance_str(self, obj):
        return '${:.2f}'.format(obj.balance() / 100)

    def fundraised_str(self, obj):
        return '${:.2f}'.format(obj.fundraised() / 100)


@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    readonly_fields = ('balance_str', 'donated_str')

    def balance_str(self, obj):
        return '${:.2f}'.format(obj.balance() / 100)

    def donated_str(self, obj):
        return '${:.2f}'.format(obj.donated() / 100)


admin.site.register(models.NonprofitCategory)
admin.site.register(models.DepositCategory)
admin.site.register(models.Deposit)
admin.site.register(models.Withdrawal)
admin.site.register(models.Entry)
admin.site.register(models.Donation)
admin.site.register(models.Transaction)
admin.site.register(models.News)
admin.site.register(models.Event)
admin.site.register(models.Post)
admin.site.register(models.Comment)
