from django.contrib import admin

import ibis.models as models

admin.site.register(models.IbisUser)
admin.site.register(models.NonprofitCategory)
admin.site.register(models.PrivacyPolicy)
admin.site.register(models.NotificationReason)
admin.site.register(models.Settings)
admin.site.register(models.Nonprofit)
admin.site.register(models.Exchange)
admin.site.register(models.Transaction)
admin.site.register(models.Article)
admin.site.register(models.Event)
admin.site.register(models.Comment)
admin.site.register(models.UserCommentVote)
