from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from allauth.socialaccount.models import SocialLogin
from rest_auth.registration.serializers import SocialLoginSerializer


class CallbackSerializer(SocialLoginSerializer):
    state = serializers.CharField()

    def validate_state(self, value):
        """
        Checks that the state is equal to the one stored in the session.
        """
        try:
            SocialLogin.verify_and_unstash_state(
                self.context['request'],
                value,
            )
        # Allauth raises PermissionDenied if the validation fails
        except PermissionDenied:
            raise ValidationError(_('State did not match.'))
        return value
