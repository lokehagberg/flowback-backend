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

    def test_delegate_can_delegate_to_themselves_only(self):
        """Test that a GroupUser who is already a delegate should be able to run group_user_delegate 
        on a pool they're already a delegate in, but won't be able to delegate to anyone besides themselves."""

        # user2 is already a delegate in self.delegate_pool (set up in setUp)
        # Test that user2 (the delegate) can delegate to their own pool (self-delegation)
        response = generate_request(
            api=GroupUserDelegateApi,
            data={
                'delegate_pool_id': self.delegate_pool.id,
                'tags': [self.tag1.id]
            },
            url_params={'group': self.group.id},
            user=self.user2  # user2 is the delegate
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the self-delegation was created
        self_delegator = GroupUserDelegator.objects.filter(delegator=self.group_user2,  # same as delegate
                                                           delegate_pool=self.delegate_pool).first()

        self.assertIsNotNone(self_delegator)
        self.assertEqual(self_delegator.tags.count(), 1)
        self.assertTrue(self_delegator.tags.filter(id=self.tag1.id).exists())

        # Now test the validation logic: a delegate trying to delegate to a different pool
        # should trigger the validation error "Delegate cannot be a delegator beside to themselves"
        different_pool = GroupUserDelegatePoolFactory(group=self.group)
        GroupUserDelegateFactory(group=self.group,
                                 group_user=self.group_user3,  # different user as delegate
                                 pool=different_pool)

        # user2 (who is a delegate) tries to delegate to a different pool
        # According to the business logic, this should fail with ValidationError
        response = generate_request(api=GroupUserDelegateApi,
                                    data={'delegate_pool_id': different_pool.id,
                                          'tags': [self.tag2.id]},
                                    url_params={'group': self.group.id},
                                    user=self.user2)  # user2 is a delegate, trying to delegate elsewhere

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delegator_removed_when_delegate_deleted(self):
        """Test to see if a delegator who's delegated to themselves is removed properly 
        when the delegate is removed."""

        # Create a new delegate pool and delegate
        new_pool = GroupUserDelegatePoolFactory(group=self.group)
        new_delegate = GroupUserDelegateFactory(
            group=self.group,
            group_user=self.group_user3,
            pool=new_pool
        )

        # Make the delegate also a delegator to themselves (self-delegation)
        self_delegator = GroupUserDelegatorFactory(
            group=self.group,
            delegator=self.group_user3,  # same as the delegate
            delegate_pool=new_pool
        )
        self_delegator.tags.add(self.tag1)

        # Verify the self-delegation exists
        self.assertTrue(
            GroupUserDelegator.objects.filter(
                delegator=self.group_user3,
                delegate_pool=new_pool
            ).exists()
        )

        # Now delete the delegate pool (which should remove the delegate)
        response = generate_request(
            api=GroupUserDelegatePoolDeleteApi,
            url_params={'group': self.group.id},
            user=self.user3  # user3 is the delegate who owns the pool
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that both the delegate pool and the self-delegator are removed
        self.assertFalse(
            GroupUserDelegatePool.objects.filter(id=new_pool.id).exists()
        )

        self.assertFalse(
            GroupUserDelegate.objects.filter(
                group_user=self.group_user3,
                pool_id=new_pool.id
            ).exists()
        )

        # Most importantly, verify that the self-delegator is also removed
        self.assertFalse(
            GroupUserDelegator.objects.filter(
                delegator=self.group_user3,
                delegate_pool_id=new_pool.id
            ).exists()
        )

    def test_cannot_delegate_same_tag_to_multiple_delegates(self):
        """A user cannot delegate the same tag to multiple delegates (pools) within the same group."""
        # Existing: user1 -> self.delegate_pool with tag1
        # Create a second delegate pool with a different delegate
        second_pool = GroupUserDelegatePoolFactory(group=self.group)
        GroupUserDelegateFactory(
            group=self.group,
            group_user=self.group_user3,
            pool=second_pool
        )

        # Try to delegate the same tag1 to the second delegate pool
        response = generate_request(api=GroupUserDelegateApi,
                                    data={'delegate_pool_id': second_pool.id, 'tags': [self.tag1.id]},
                                    url_params={'group': self.group.id},
                                    user=self.user1)

        # Should not be permitted
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Delegate to a different tag, then update to tag1 and see if it fails
        generate_request(api=GroupUserDelegateApi,
                         data={'delegate_pool_id': second_pool.id, 'tags': [self.tag2.id]},
                         url_params={'group': self.group.id},
                         user=self.user1)

        response = generate_request(api=GroupUserDelegateUpdateApi,
                                    data={'delegate_pool_id': second_pool.id, 'tags': [self.tag1.id]},
                                    url_params={'group': self.group.id},
                                    user=self.user1)

        # Should not be permitted
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'][0], 'User already delegated to same tag in another pool')
