from django.contrib import admin

import notifications.models as models


@admin.register(models.Email)
class EmailAdmin(admin.ModelAdmin):
    raw_id_fields = ['notification']


admin.site.register(models.Notifier)
admin.site.register(models.Notification)
admin.site.register(models.EmailTemplateWelcome)
admin.site.register(models.EmailTemplateMessageDirect)
admin.site.register(models.EmailTemplateMessageChannel)
admin.site.register(models.EmailTemplateFollow)
admin.site.register(models.EmailTemplateUBP)
admin.site.register(models.EmailTemplateDeposit)
admin.site.register(models.EmailTemplateWithdrawal)
admin.site.register(models.EmailTemplateDonation)
admin.site.register(models.EmailTemplateReward)
admin.site.register(models.EmailTemplateComment)
admin.site.register(models.EmailTemplateMention)
