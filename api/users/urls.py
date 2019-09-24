"""
Implementations of Django routing for Ibis users
"""

from django.urls import include, path
from rest_auth.registration.views import SocialAccountDisconnectView

from . import views

# url routes for Google authentication
google_urlpatterns = [
    path('auth-server/', views.GoogleLogin.as_view(), name='google_auth_server'),
    path(
        'login/',
        views.GoogleCallbackCreate.as_view(),
        name='google_callback_login',
    ),
    path(
        'connect/',
        views.GoogleCallbackConnect.as_view(),
        name='google_callback_connect',
    ),
]

# url routes for Facebook authentication
facebook_urlpatterns = [
    path('auth-server/', views.FacebookLogin.as_view(), name='facebook_auth_server'),
    path(
        'login/',
        views.FacebookCallbackCreate.as_view(),
        name='facebook_callback_login',
    ),
    path(
        'connect/',
        views.FacebookCallbackConnect.as_view(),
        name='facebook_callback_connect',
    ),
]

# redirect to site-specific authentication
urlpatterns = [
    path('social/google/', include(google_urlpatterns)),
    path('social/facebook/', include(facebook_urlpatterns)),
    path(
        'user/accounts/<int:pk>/disconnect/',
        SocialAccountDisconnectView.as_view(),
        name='social_account_disconnect',
    ),
]
