"""
Implementations of Django views for Ibis users

Since we are not using the traditional Django MVC framework, all of
these views need to be serialized by objects from .serializers.py
"""

from django.utils.translation import gettext as _

from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.base import AuthAction
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
from rest_auth.registration.views import SocialConnectView, SocialLoginView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .serializers import CallbackSerializer
from .adapters import GoogleOAuth2AdapterCustom


class CallbackMixin:
    """
    Mixin which provides Oauth definitions for inheriting subclass
    """

    adapter_class = GoogleOAuth2AdapterCustom
    client_class = OAuth2Client
    serializer_class = CallbackSerializer

    # Not the prettiest but single source of truth
    @property
    def callback_url(self):
        url = self.adapter_class(self.request).get_callback_url(
            self.request,
            None,
        )
        return url


class Login(APIView):
    """
    View for returning Ibis-specific url to submit Google Oauth2 request

    The user submits a blank post request to this view and receives,
    view a serialized JSON object, a url that embedds an oauth
    'client_id' to identify the app with google, a 'redirect_uri' to
    redirect the user after login, and a 'state' to secure against
    tampering through the entire process.
    """

    adapter_class = GoogleOAuth2AdapterCustom
    permission_classes = (AllowAny, )

    def post(self, request, format=None):
        # You should have CSRF protection enabled, see
        # https://security.stackexchange.com/a/104390 (point 3).
        # Therefore this is a POST endpoint.
        # This code is inspired by `OAuth2LoginView.dispatch`.
        adapter = self.adapter_class(request)
        provider = adapter.get_provider()
        app = provider.get_app(request)
        view = OAuth2LoginView()
        view.request = request
        view.adapter = adapter
        client = view.get_client(request, app)
        action = AuthAction.AUTHENTICATE
        auth_params = provider.get_auth_params(request, action)
        client.state = SocialLogin.stash_state(request)
        url = client.get_redirect_url(adapter.authorize_url, auth_params)
        return Response({'url': url})


class CallbackCreate(CallbackMixin, SocialLoginView):
    """
    View for creating/logging in a user into the Ibis app

    After the user obtains logs into Google and obtains an oauth code,
    they should be directed here. The post request to CallbackCreate
    consumes the code and state, completes the authentication process
    with Google, and returns a token to authenticate the user. A new
    account is automatically created if the user is new.
    """


# NOTE: this functionality has not yet been tested
class CallbackConnect(CallbackMixin, SocialConnectView):
    """
    Connects a provider's user account to the currently logged in user.
    """

    # You can override this method here if you don't want to
    # receive a token. Omit it otherwise.
    def get_response(self):
        return Response({'detail': _('Connection completed.')})
