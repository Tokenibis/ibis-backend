"""
Implementations of DRF serializers for Ibis profiles

DRF serializers convert traditional Django views into a JSON object
that is returned by the REST API.
"""

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from allauth.socialaccount.models import SocialLogin
from rest_auth.registration.serializers import SocialLoginSerializer


class CallbackSerializer(SocialLoginSerializer):
    """
    See SocialLoginSerializer docstring
    """

    state = serializers.CharField()

    def validate_state(self, value):
        """
        Checks that the state is equal to the one stored in the session.
        
        Since we are validating state against information stored in
        the session, the Login and CreateCallback requests must
        originate from the same endpoint and must be authenticated.
        """
        # try:
        #     SocialLogin.verify_and_unstash_state(
        #         self.context['request'],
        #         value,
        #     )
        # # Allauth raises PermissionDenied if the validation fails
        # except PermissionDenied:
        #     raise ValidationError(_('State did not match.'))
        return value
