from rest_framework import serializers

from flowback.group.models import Group
from flowback.user.serializers import BasicUserSerializer


class BasicGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name', 'image', 'cover_image', 'hide_poll_users')


class GroupUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    user = BasicUserSerializer(required=False)
    is_admin = serializers.BooleanField(required=False)
    active = serializers.BooleanField(required=False)

    permission_id = serializers.IntegerField(required=False, allow_null=True)
    permission_name = serializers.CharField(required=False, source='permission.role_name', default='Member')
    group_id = serializers.IntegerField(required=False)
    group_name = serializers.CharField(required=False, source='group.name')
    group_image = serializers.CharField(required=False, source='group.image')


class WorkGroupSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
