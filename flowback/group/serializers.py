from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from flowback.group.models import Group, GroupUser
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

    permission_id = SerializerMethodField()
    permission_name = SerializerMethodField()
    group_id = serializers.IntegerField(required=False)
    group_name = serializers.CharField(required=False, source='group.name')
    group_image = serializers.CharField(required=False, source='group.image')

    def get_permission_id(self, obj):
        if obj.permission:
            return obj.permission_id

        return obj.group.default_permission_id

    def get_permission_name(self, obj):
        if obj.permission:
            return obj.permission.role_name

        return obj.group.default_permission.role_name

    def __init__(self, *args, hide_relevant_users=False, **kwargs):
        self.hide_relevant_users = hide_relevant_users

        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        if isinstance(instance, int):
            group_user = GroupUser.objects.get(id=instance)
        else:
            group_user = instance

        if self.hide_relevant_users and group_user.group.hide_poll_users:
            return None

        return super().to_representation(instance)


class WorkGroupSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
