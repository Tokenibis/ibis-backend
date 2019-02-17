from django.urls import include, path
from rest_auth.registration.views import SocialAccountDisconnectView

from . import views

google_urlpatterns = [
    path('auth-server/', views.Login.as_view(), name='google_auth_server'),
    path(
        'login/',
        views.CallbackCreate.as_view(),
        name='google_callback_login',
    ),
    path(
        'connect/',
        views.CallbackConnect.as_view(),
        name='google_callback_connect',
    ),
]

urlpatterns = [
    path('social/google/', include(google_urlpatterns)),
    path(
        'user/accounts/<int:pk>/disconnect/',
        SocialAccountDisconnectView.as_view(),
        name='social_account_disconnect',
    ),
]
