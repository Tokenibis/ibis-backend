from django.contrib import admin

import ibis.models as models
from django.contrib.auth.admin import UserAdmin


@admin.register(models.Organization)
class OrganizationAdmin(UserAdmin):
    readonly_fields = ('balance_str', 'fundraised_str')

    def balance_str(self, obj):
        return '${:.2f}'.format(obj.balance() / 100)

    def fundraised_str(self, obj):
        return '${:.2f}'.format(obj.fundraised() / 100)


@admin.register(models.Person)
class PersonAdmin(UserAdmin):
    readonly_fields = ('balance_str', 'donated_str')

    def balance_str(self, obj):
        return '${:.2f}'.format(obj.balance() / 100)

    def donated_str(self, obj):
        return '${:.2f}'.format(obj.donated() / 100)


@admin.register(models.Bot)
class BotAdmin(UserAdmin):
    readonly_fields = ('balance_str', 'rewarded_str')

    def balance_str(self, obj):
        return '${:.2f}'.format(obj.balance() / 100)

    def rewarded_str(self, obj):
        return '${:.2f}'.format(obj.rewarded() / 100)


class EntryOrganizationAdmin(admin.ModelAdmin):
    exclude = (
        'score',
        'bookmark',
        'like',
        'mention',
        'rsvp',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = models.User.objects.filter(
                organization__isnull=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(models.News, EntryOrganizationAdmin)
admin.site.register(models.Event, EntryOrganizationAdmin)

admin.site.register(models.OrganizationCategory)
admin.site.register(models.ExchangeCategory)
admin.site.register(models.Deposit)
admin.site.register(models.Withdrawal)
admin.site.register(models.Entry)
admin.site.register(models.Donation)
admin.site.register(models.Reward)
admin.site.register(models.Post)
admin.site.register(models.Activity)
admin.site.register(models.Comment)
