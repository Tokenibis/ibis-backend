from rest_framework import serializers
from users.models import GeneralUser


class PasswordLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
    )


class PasswordChangeSerializer(serializers.Serializer):
    model = GeneralUser
    password_old = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
    )
    password_new = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
    )


class PaymentSerializer(serializers.Serializer):
    orderID = serializers.CharField(read_only=True)
