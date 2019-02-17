from rest_framework import serializers

from .models import Transaction
from profiles.models import Profile


class ProfilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('id', 'username', 'is_active', 'last_login', 'date_joined')


class TransactionsSerializer(serializers.ModelSerializer):

    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()

    def get_sender_name(self, transaction):
        return transaction.sender.username

    def get_receiver_name(self, transaction):
        return transaction.receiver.username

    class Meta:
        model = Transaction
        fields = ('amount', 'datetime', 'sender_name', 'receiver_name')
