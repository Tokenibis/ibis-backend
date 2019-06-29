from django.urls import path
from .views import ListUsersView, ListTransfersView

urlpatterns = [
    path(
        'transfers/',
        ListTransfersView.as_view(),
        name='transfers-all'),
    path('users/', ListUsersView.as_view(), name='users-all'),
]
