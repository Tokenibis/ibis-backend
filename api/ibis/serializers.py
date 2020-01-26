from rest_framework import serializers


class PasswordLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
    )


class PaymentSerializer(serializers.Serializer):
    orderID = serializers.CharField(read_only=True)
