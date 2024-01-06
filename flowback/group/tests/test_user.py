import json

from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from .factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory
from ..views.user import GroupUserListApi


class GroupUserTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = GroupUserFactory(group=self.group)

        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = [GroupUserFactory(group=self.group) for _ in range(3)]

    def test_list_users(self):
        GroupUserDelegateFactory(group=self.group, group_user=self.group_user_one)

        factory = APIRequestFactory()
        user = self.group_user_creator.user
        view = GroupUserListApi.as_view()

        request = factory.get('')
        force_authenticate(request, user)
        response = view(request, group=self.group.id)
        data = json.loads(response.rendered_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['results'][0].get('is_delegate'), False)
        self.assertEqual(data['results'][1].get('is_delegate'), True)
        self.assertEqual(data['results'][2].get('is_delegate'), False)
        self.assertEqual(data['results'][3].get('is_delegate'), False)
