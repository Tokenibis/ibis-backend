from rest_framework import serializers
from .models import Account, Transaction


class AccountsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Account
        fields = ('nickname', 'create_time')


class TransactionsSerializer(serializers.ModelSerializer):

    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()

    def get_sender_name(self, transaction):
        return transaction.sender.nickname
    
    def get_receiver_name(self, transaction):
        return transaction.receiver.nickname

    class Meta:
        model = Transaction
        fields = ('amount', 'datetime', 'sender_name', 'receiver_name')
