from rest_framework import generics
from .models import Profile, Transaction
from .serializers import TransactionsSerializer
from profiles.serializers import ProfilesSerializer


class ListProfilesView(generics.ListAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfilesSerializer


class ListTransactionsView(generics.ListAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionsSerializer
