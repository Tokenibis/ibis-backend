from django.urls import path
from .views import ListProfilesView, ListTransactionsView

urlpatterns = [
    path(
        'transactions/',
        ListTransactionsView.as_view(),
        name='transactions-all'),
    path('profiles/', ListProfilesView.as_view(), name='profiles-all'),
]
