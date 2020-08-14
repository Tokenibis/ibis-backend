from django.urls import path
import notifications.views as views

urlpatterns = [
    path(
        'settings/<int:pk>/<str:token>/',
        views.SettingsView.as_view(),
        name='settings',
    ),
    path(
        'organization_settings/<int:pk>/<str:token>/',
        views.OrganizationSettingsView.as_view(),
        name='organization_settings',
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
    path(
        'app_link/<str:gid>/',
        views.AppLinkView.as_view(),
        name='app_link',
    ),
]
