from rest_framework import serializers


class PaymentSerializer(serializers.Serializer):
    orderID = serializers.CharField(read_only=True)
