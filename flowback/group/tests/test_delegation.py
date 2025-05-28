from rest_framework.test import APITestCase
from rest_framework import status

from flowback.common.tests import generate_request
from flowback.group.notify import notify_group_user_delegate_pool_poll_vote_update
from flowback.notification.models import NotificationSubscription, NotificationChannel, Notification
from flowback.group.views.delegate import (
    GroupUserDelegatePoolListApi,
    GroupUserDelegateListApi,
    GroupUserDelegatePoolCreateApi,
    GroupUserDelegatePoolDeleteApi,
    GroupUserDelegatePoolNotificationSubscribeAPI,
    GroupUserDelegateApi,
    GroupUserDelegateUpdateApi,
    GroupUserDelegateDeleteApi
)
from flowback.group.tests.factories import (
    UserFactory,
    GroupFactory,
    GroupUserFactory,
    GroupTagsFactory,
    GroupUserDelegatePoolFactory,
    GroupUserDelegateFactory,
    GroupUserDelegatorFactory
)
from flowback.group.models import (
    GroupUser,
    GroupUserDelegatePool,
    GroupUserDelegate,
    GroupUserDelegator
)
from flowback.poll.tests.factories import PollFactory


class GroupDelegationTestCase(APITestCase):
    def setUp(self):
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user3 = UserFactory()

        self.group = GroupFactory(created_by=self.user1)

        self.group_user1 = self.group.group_user_creator

        self.group_user2 = GroupUserFactory(user=self.user2, group=self.group)
        self.group_user3 = GroupUserFactory(user=self.user3, group=self.group)

        self.tag1 = GroupTagsFactory(group=self.group, name="tag1")
        self.tag2 = GroupTagsFactory(group=self.group, name="tag2")

        self.delegate_pool = GroupUserDelegatePoolFactory(group=self.group)

        self.delegate = GroupUserDelegateFactory(
            group=self.group,
            group_user=self.group_user2,
            pool=self.delegate_pool
        )

        self.delegator = GroupUserDelegatorFactory(
            group=self.group,
            delegator=self.group_user1,
            delegate_pool=self.delegate_pool
        )

        self.delegator.tags.add(self.tag1)

    def test_get_delegate_pools(self):
        # Test getting delegate pools
        response = generate_request(
            api=GroupUserDelegatePoolListApi,
            url_params={'group': self.group.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreaterEqual(len(response.data['results']), 1)

        # Test with filter
        response = generate_request(
            api=GroupUserDelegatePoolListApi,
            data={'id': self.delegate_pool.id},
            url_params={'group': self.group.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.delegate_pool.id)

    def test_get_delegates(self):
        response = generate_request(
            api=GroupUserDelegateListApi,
            url_params={'group': self.group.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('results', response.data)

        # Test with filter
        response = generate_request(
            api=GroupUserDelegateListApi,
            data={'tag_id': self.tag1.id},
            url_params={'group': self.group.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('results', response.data)

    def test_create_delegate_pool(self):
        """Test GroupUserDelegatePoolCreateApi"""
        # Test creating a delegate pool
        response = generate_request(
            api=GroupUserDelegatePoolCreateApi,
            data={'blockchain_id': 123},
            url_params={'group': self.group.id},
            user=self.user3
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the pool was created
        self.assertTrue(
            GroupUserDelegatePool.objects.filter(
                group=self.group,
                blockchain_id=123
            ).exists()
        )

    def test_delete_delegate_pool(self):
        response = generate_request(api=GroupUserDelegatePoolDeleteApi,
                                    url_params={'group': self.group.id},
                                    data={'delegate_pool_id': self.delegate_pool.id},
                                    user=self.user2)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(GroupUserDelegatePool.objects.filter(group=self.group).exists())

    def test_create_delegate(self):
        new_pool = GroupUserDelegatePoolFactory(group=self.group)

        # Test creating a delegate for user3
        response = generate_request(
            api=GroupUserDelegateApi,
            data={
                'delegate_pool_id': new_pool.id,
                'tags': [self.tag1.id, self.tag2.id]
            },
            url_params={'group': self.group.id},
            user=self.user3
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the delegate was created
        delegator = GroupUserDelegator.objects.filter(
            delegator=self.group_user3,
            delegate_pool=new_pool
        ).first()

        self.assertIsNotNone(delegator)
        self.assertEqual(delegator.tags.count(), 2)

    def test_update_delegate(self):
        self.skipTest("This feature is not working yet, refer to delete and recreating the delegator instead.")
        # response = generate_request(api=GroupUserDelegateUpdateApi,
        #                             data=dict(delegate_pool_id=self.delegate_pool.id,
        #                                       tags=f'{self.tag2.id}'),
        #                             url_params=dict(group=self.group.id),
        #                             user=self.user1)
        #
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # print(GroupUserDelegator.objects.get(delegator=self.group_user1).tags.first().name)
        # self.assertTrue(GroupUserDelegator.objects.filter(delegator=self.group_user1,
        #                                                   tags__in=[self.tag2]).exists())

    def test_delete_delegate(self):
        """Test GroupUserDelegateDeleteApi"""
        # Create a delegator for user3
        new_pool = GroupUserDelegatePoolFactory(group=self.group)
        delegator = GroupUserDelegatorFactory(
            group=self.group,
            delegator=self.group_user3,
            delegate_pool=new_pool
        )

        # Test deleting the delegate
        response = generate_request(
            api=GroupUserDelegateDeleteApi,
            data={'delegate_pool_id': new_pool.id},
            url_params={'group': self.group.id},
            user=self.user3
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the delegate was deleted
        self.assertFalse(
            GroupUserDelegator.objects.filter(
                delegator=self.group_user3,
                delegate_pool=new_pool
            ).exists()
        )

    def test_delegate_pool_notification_subscribe(self):
        # Test subscribing with tags
        tags = ['poll_vote_update']
        response = generate_request(
            api=GroupUserDelegatePoolNotificationSubscribeAPI,
            data={'tags': tags},
            url_params={'delegate_pool_id': self.delegate_pool.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # Verify subscription was created with correct tags
        subscription = NotificationSubscription.objects.filter(
            user=self.user1,
            channel=self.delegate_pool.notification_channel
        ).first()

        self.assertIsNotNone(subscription)
        self.assertEqual(set(subscription.tags), set(tags))

        poll = PollFactory(created_by=self.group_user3, tag=self.tag1)
        notify_group_user_delegate_pool_poll_vote_update(message="Test test!",
                                                         action=NotificationChannel.Action.UPDATED,
                                                         delegate_pool=self.delegate_pool,
                                                         poll=poll)

        self.assertTrue(Notification.objects.filter(notification_object__channel__notificationsubscription=subscription,
                                                    notification_object__message="Test test!",
                                                    notification_object__data__poll_id=poll.id))
