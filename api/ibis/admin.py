from django.contrib import admin

import ibis.models as models

admin.site.register(models.Follow)
admin.site.register(models.Exchange)
admin.site.register(models.Post)
admin.site.register(models.Transaction)
admin.site.register(models.Article)
admin.site.register(models.Event)
admin.site.register(models.Comment)
admin.site.register(models.Upvote)
admin.site.register(models.Downvote)
admin.site.register(models.RSVP)
