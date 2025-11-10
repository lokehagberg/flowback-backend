import json

from rest_framework import status
from rest_framework.test import APITestCase
from .factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory
from ..views.user import GroupUserListApi
from ...common.tests import generate_request

# New imports for leave test
from flowback.group.services.group import group_leave
from flowback.group.models import GroupUser
from flowback.kanban.models import KanbanSubscription
from flowback.notification.models import NotificationSubscription
from flowback.chat.models import MessageChannelParticipant


class GroupUserTest(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = self.group.group_user_creator

        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = GroupUserFactory.create_batch(3, group=self.group)

    def test_list_users(self):
        GroupUserDelegateFactory(group=self.group, group_user=self.group_user_one)

        user = self.group_user_creator.user

        # Basic test
        response = generate_request(api=GroupUserListApi,
                                    user=user,
                                    url_params=dict(group_id=self.group.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['results'][0].get('delegate_pool_id'), None)
        self.assertEqual(response.data['results'][1].get('delegate_pool_id'), True)
        self.assertEqual(response.data['results'][2].get('delegate_pool_id'), None)
        self.assertEqual(response.data['results'][3].get('delegate_pool_id'), None)

        # Test delegates only
        response = generate_request(api=GroupUserListApi,
                                    user=user,
                                    url_params=dict(group_id=self.group.id),
                                    data=dict(is_delegate=True))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0].get('delegate_pool_id'), True)

    def test_group_user_leave_cleans_up_subscriptions(self):
        # Arrange: pick a non-creator group user
        member: GroupUser = self.group_user_one

        # Subscribe the user to the group's notification channel (any valid tag)
        self.group.notification_channel.subscribe(user=member.user, tags=("group",))

        # Ensure preconditions
        self.assertTrue(MessageChannelParticipant.objects.filter(id=member.chat_participant_id).exists())
        self.assertTrue(NotificationSubscription.objects.filter(channel=self.group.notification_channel).exists())
        self.assertTrue(KanbanSubscription.objects.filter(kanban=member.user.kanban, target=self.group.kanban).exists())

        # Act: user leaves the group
        group_leave(user=member.user.id, group=self.group.id)

        # Refresh objects
        member.refresh_from_db()

        # Assert: GroupUser becomes inactive
        self.assertFalse(member.active)

        # Kanban subscription removed
        self.assertFalse(KanbanSubscription.objects.filter(kanban=member.user.kanban, target=self.group.kanban).exists())

        # Chat participant removed
        self.assertFalse(MessageChannelParticipant.objects.filter(id=member.chat_participant_id, active=True).exists())

        # Notification subscriptions to this group's channel removed
        self.assertFalse(NotificationSubscription.objects.filter(channel__in=self.group.notification_channel.descendants(include_self=True)).exists())
