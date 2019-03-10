from django.urls import path
from .views import ListUsersView, ListTransactionsView

urlpatterns = [
    path(
        'transactions/',
        ListTransactionsView.as_view(),
        name='transactions-all'),
    path('users/', ListUsersView.as_view(), name='users-all'),
]
