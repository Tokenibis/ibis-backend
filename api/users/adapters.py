"""
Implementations Django Allauth adapters for Ibis users
"""

from django.conf import settings

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.microsoft.views import MicrosoftGraphOAuth2Adapter
from rest_framework.exceptions import AuthenticationFailed


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, *args, **kwargs):
        # only prevent signup if app specifically requested signin
        if request.POST.get('mode') == 'sign_in':
            raise AuthenticationFailed(
                'Hm... there are no Token Ibis users with this account. Please try to "sign up" instead.'
            )


class GoogleOAuth2AdapterCustom(GoogleOAuth2Adapter):
    """Extension of Google Adapter to reference ibis frontend url

    The GoogleOauth2Adapter class provided by allauth uses logic to
    set the callback link (aka redirect_uri) that assumes a
    traditional website with an exposed backend API. Since Ibis
    coordinates the Oauth2 protocol behind a React frontend, we need
    to override the callback url to the single front-facing app url.
    """

    def get_callback_url(self, request, app):
        return settings.REDIRECT_URL_GOOGLE


class FacebookOAuth2AdapterCustom(FacebookOAuth2Adapter):
    """Extension of Facebook Adapter to reference ibis frontend url

    The FacebookOauth2Adapter class provided by allauth uses logic to
    set the callback link (aka redirect_uri) that assumes a
    traditional website with an exposed backend API. Since Ibis
    coordinates the Oauth2 protocol behind a React frontend, we need
    to override the callback url to the single front-facing app url.
    """

    def get_callback_url(self, request, app):
        return settings.REDIRECT_URL_FACEBOOK


class MicrosoftOAuth2AdapterCustom(MicrosoftGraphOAuth2Adapter):
    """Extension of Microsoft Adapter to reference ibis frontend url

    The MicrosoftOauth2Adapter class provided by allauth uses logic to
    set the callback link (aka redirect_uri) that assumes a
    traditional website with an exposed backend API. Since Ibis
    coordinates the Oauth2 protocol behind a React frontend, we need
    to override the callback url to the single front-facing app url.
    """

    def get_callback_url(self, request, app):
        return settings.REDIRECT_URL_MICROSOFT
