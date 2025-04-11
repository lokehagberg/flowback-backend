from rest_framework import serializers

from flowback.user.models import User


class BasicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'profile_image', 'banner_image', 'public_status', 'chat_status')
