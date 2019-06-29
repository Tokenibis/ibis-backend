from rest_framework import serializers

from .models import Transfer
from users.models import User


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'is_active', 'last_login', 'date_joined')


class TransfersSerializer(serializers.ModelSerializer):

    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()

    def get_sender_name(self, transfer):
        return transfer.sender.username

    def get_receiver_name(self, transfer):
        return transfer.receiver.username

    class Meta:
        model = Transfer
        fields = ('amount', 'datetime', 'sender_name', 'receiver_name')
