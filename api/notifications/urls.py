from django.urls import path
import notifications.views as views

urlpatterns = [
    path(
        'settings/<int:pk>/<str:token>/',
        views.SettingsView.as_view(),
        name='settings',
    ),
    path(
        'nonprofit_settings/<int:pk>/<str:token>/',
        views.NonprofitSettingsView.as_view(),
        name='nonprofit_settings',
    ),
    path(
        'unsubscribe/<int:pk>/<str:token>/',
        views.UnsubscribeView.as_view(),
        name='unsubscribe',
    ),
    path(
        'settings_success/',
        views.SettingsSuccess.as_view(),
        name='settings_success',
    ),
    path(
        'unsubscribe_success/',
        views.UnsubscribeSuccess.as_view(),
        name='unsubscribe_success',
    ),
    path(
        'donation_message/<str:name>/',
        views.DonationMessageView.as_view(),
        name='donation_message',
    ),
]
