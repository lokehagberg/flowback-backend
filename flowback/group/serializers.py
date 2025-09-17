from rest_framework import serializers

from flowback.group.models import Group
from flowback.user.serializers import BasicUserSerializer


class BasicGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name', 'image', 'cover_image', 'hide_poll_users')


class BasicGroupUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    group = BasicGroupSerializer()
    user = BasicUserSerializer()
