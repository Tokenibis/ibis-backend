from django.urls import path
from .views import ListAccountsView, ListTransactionsView

urlpatterns = [
    path(
        'transactions/',
        ListTransactionsView.as_view(),
        name='transactions-all'),
    path('accounts/', ListAccountsView.as_view(), name='accounts-all'),
]
