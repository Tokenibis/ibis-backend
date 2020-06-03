from django.db import models
from model_utils.models import TimeStampedModel

from users.models import User


class Log(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    response_code = models.TextField(blank=True, null=True)
    graphql_operation = models.TextField(blank=True, null=True)
    graphql_variables = models.TextField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    pwa_standalone = models.NullBooleanField(blank=True, null=True)

    def __str__(self):
        return '{}:{}:{}'.format(
            self.pk,
            self.user.username if hasattr(self.user, 'username') else 'None',
            self.graphql_operation,
        )
