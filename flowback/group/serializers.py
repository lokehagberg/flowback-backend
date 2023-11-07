from rest_framework import serializers

from flowback.group.models import Group, GroupUser
from flowback.user.serializers import BasicUserSerializer

class BasicGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name', 'image', 'cover_image', 'hide_poll_users')


class GroupUserSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer()

    permission_id = serializers.IntegerField(allow_null=True)
    permission_name = serializers.CharField(source='permission.role_name', default='Member')
    group_name = serializers.CharField(source='group.name')
    group_image = serializers.CharField(source='group.image')

    class Meta:
        model = GroupUser
        fields = ('id',
                  'user',
                  'is_admin',
                  'permission_name',
                  'permission_id',
                  'group_name',
                  'group_image',
                  'active')
