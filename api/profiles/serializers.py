from rest_framework import serializers
from .models import Profile


class ProfilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('nickname', 'create_time')
