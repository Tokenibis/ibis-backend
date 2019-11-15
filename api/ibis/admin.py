from django.contrib import admin

import ibis.models as models

admin.site.register(models.NonprofitCategory)
admin.site.register(models.PrivacyPolicy)
admin.site.register(models.NotificationReason)
admin.site.register(models.Settings)
admin.site.register(models.Person)
admin.site.register(models.Nonprofit)
admin.site.register(models.Deposit)
admin.site.register(models.Withdrawal)
admin.site.register(models.Entry)
admin.site.register(models.Donation)
admin.site.register(models.Transaction)
admin.site.register(models.News)
admin.site.register(models.Event)
admin.site.register(models.Votable)
admin.site.register(models.Post)
admin.site.register(models.Comment)
admin.site.register(models.Vote)
