from django.contrib import admin

import notifications.models as models

admin.site.register(models.Notifier)
admin.site.register(models.Notification)
admin.site.register(models.Email)
admin.site.register(models.EmailTemplateWelcome)
admin.site.register(models.EmailTemplateMessage)
admin.site.register(models.EmailTemplateFollow)
admin.site.register(models.EmailTemplateUBP)
admin.site.register(models.EmailTemplateDeposit)
admin.site.register(models.EmailTemplateWithdrawal)
admin.site.register(models.EmailTemplateDonation)
admin.site.register(models.EmailTemplateReward)
admin.site.register(models.EmailTemplateComment)
admin.site.register(models.EmailTemplateMention)
