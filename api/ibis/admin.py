from django.contrib import admin

import ibis.models as models


@admin.register(models.Nonprofit)
class NonprofitAdmin(admin.ModelAdmin):
    readonly_fields = ('balance_str', 'fundraised_str')

    def balance_str(self, obj):
        return '${:.2f}'.format(obj.balance() / 100)

    def fundraised_str(self, obj):
        return '${:.2f}'.format(obj.fundraised() / 100)


class EntryNonprofitAdmin(admin.ModelAdmin):
    exclude = (
        'score',
        'bookmark',
        'like',
        'mention',
        'rsvp',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = models.IbisUser.objects.filter(
                nonprofit__isnull=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(models.News, EntryNonprofitAdmin)
admin.site.register(models.Event, EntryNonprofitAdmin)

admin.site.register(models.NonprofitCategory)
admin.site.register(models.DepositCategory)
admin.site.register(models.Deposit)
admin.site.register(models.Withdrawal)
admin.site.register(models.Entry)
admin.site.register(models.Donation)
admin.site.register(models.Transaction)
admin.site.register(models.Comment)
