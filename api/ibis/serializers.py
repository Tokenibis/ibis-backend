from rest_framework import serializers

from .models import IbisUser


class LoginFormSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=17)
