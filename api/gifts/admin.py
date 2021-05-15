from django.contrib import admin
import gifts.models as models


@admin.register(models.Gift)
class GiftAdmin(admin.ModelAdmin):
    list_display = ('gift', 'gift_type', 'action', 'amount')

    def gift(self, obj):
        return '{}\'s Gift'.format(obj.user)

    def gift_type(self, obj):
        return obj.choice

    def action(self, obj):
        if obj.choice and not obj.processed:
            return 'TODO',
        elif obj.choice and obj.processed:
            return 'DONE',
        else:
            return None

    def amount(self, obj):
        return '${:.2f}'.format(
            obj.withdrawal.amount / 100) if obj.withdrawal else None


admin.site.register(models.GiftType)
