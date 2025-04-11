import json

from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from .factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory
from ..views.user import GroupUserListApi
from ...common.tests import generate_request


class GroupUserTest(APITransactionTestCase):
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
                                    url_params=dict(group_id=1))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['results'][0].get('delegate_pool_id'), None)
        self.assertEqual(response.data['results'][1].get('delegate_pool_id'), True)
        self.assertEqual(response.data['results'][2].get('delegate_pool_id'), None)
        self.assertEqual(response.data['results'][3].get('delegate_pool_id'), None)

        # Test delegates only
        response = generate_request(api=GroupUserListApi,
                                    user=user,
                                    url_params=dict(group_id=1),
                                    data=dict(is_delegate=True))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0].get('delegate_pool_id'), True)
