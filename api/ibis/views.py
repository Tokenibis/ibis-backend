from rest_framework import generics
from .models import Account, Transaction
from .serializers import AccountsSerializer, TransactionsSerializer


class ListAccountsView(generics.ListAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountsSerializer


class ListTransactionsView(generics.ListAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionsSerializer
