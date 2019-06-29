from rest_framework import generics
from .models import User, Transfer
from .serializers import UsersSerializer, TransfersSerializer


class ListUsersView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UsersSerializer


class ListTransfersView(generics.ListAPIView):
    queryset = Transfer.objects.all()
    serializer_class = TransfersSerializer
