from rest_framework import generics
from .models import User, Transaction
from .serializers import UsersSerializer, TransactionsSerializer


class ListUsersView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UsersSerializer


class ListTransactionsView(generics.ListAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionsSerializer
