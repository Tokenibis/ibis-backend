"""
Implementations Django Allauth adapters for Ibis users
"""

from django.conf import settings

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter


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
