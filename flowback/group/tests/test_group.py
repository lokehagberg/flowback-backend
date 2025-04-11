import json
from pprint import pprint

from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase

from flowback.common.tests import generate_request
from flowback.group.models import GroupUser, Group, GroupUserInvite
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, WorkGroupUserFactory
from flowback.group.views.group import GroupListApi, GroupCreateApi
from flowback.group.views.user import GroupInviteApi, GroupJoinApi, GroupInviteAcceptApi, GroupInviteListApi, \
    GroupUserListApi
from flowback.user.models import User
from flowback.user.tests.factories import UserFactory


class GroupTest(APITransactionTestCase):
    def setUp(self):
        (self.group_one,
         self.group_two,
         self.group_three) = [GroupFactory.create(public=True) for x in range(3)]

        (self.group_user_creator_one,
         self.group_user_creator_two,
         self.group_user_creator_three) = GroupUser.objects.order_by('id').all()

        self.group_no_direct = GroupFactory.create(public=True, direct_join=False)
        self.group_no_direct_user_creator = GroupUser.objects.get(user=self.group_no_direct.created_by)

        self.group_private = GroupFactory.create(public=False)
        self.group_private_user_creator = GroupUser.objects.get(user=self.group_private.created_by)

        self.groupless_user = UserFactory()

    def test_group_list(self):
        factory = APIRequestFactory()
        user = self.group_user_creator_two.user
        view = GroupListApi.as_view()

        request = factory.get('', data=dict(limit=10))
        force_authenticate(request, user=user)
        response = view(request)

        data = json.loads(response.rendered_content)
        pprint(data)

    # Also tests if work_group is being displayed in response
    def test_group_user_list(self):
        work_group_user = WorkGroupUserFactory(group_user=self.group_user_creator_one)

        response = generate_request(api=GroupUserListApi,
                                    url_params=dict(group=self.group_user_creator_one.group.id),
                                    user=self.group_user_creator_one.user)

        self.assertTrue(response.status_code == status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['work_groups'][0], work_group_user.work_group.name)

    def test_group_create(self):
        factory = APIRequestFactory()
        user = self.group_user_creator_two.user
        view = GroupCreateApi.as_view()
        data = dict(name="test",
                    description="test",
                    direct_join=True)

        request = factory.post('', data=data)
        force_authenticate(request, user=user)
        response = view(request)

        data = json.loads(response.rendered_content)
        pprint(data)

    def group_invite(self, group_user: GroupUser, to: User):
        factory = APIRequestFactory()
        view = GroupInviteApi.as_view()

        request = factory.post('', data=dict(to=to.id))
        force_authenticate(request, group_user.user)
        return view(request, group=group_user.group)

    def group_join(self, user: User, group: Group):
        factory = APIRequestFactory()
        view = GroupJoinApi.as_view()

        request = factory.post('')
        force_authenticate(request, user)
        return view(request, group=group.id)

    def test_group_invite(self):
        response = self.group_invite(self.group_no_direct_user_creator, self.groupless_user)
        pprint(response.data)

    def test_group_invite_accept(self):
        self.group_invite(self.group_no_direct_user_creator, self.groupless_user)

        factory = APIRequestFactory()
        user = self.groupless_user
        view = GroupInviteAcceptApi.as_view()
        request = factory.post('')
        force_authenticate(request, user)
        view(request, group=self.group_no_direct.id)

        self.assertTrue(GroupUser.objects.filter(user_id=self.groupless_user, group=self.group_no_direct).exists())

    def test_group_invite_accept_no_invite(self):
        factory = APIRequestFactory()
        user = self.groupless_user
        view = GroupInviteAcceptApi.as_view()
        request = factory.post('')
        force_authenticate(request, user)
        view(request, group=self.group_no_direct.id)

        self.assertFalse(GroupUser.objects.filter(user_id=self.groupless_user, group=self.group_no_direct).exists())

    def test_group_request_invite(self):
        self.group_join(self.groupless_user, self.group_no_direct)
        self.assertTrue(GroupUserInvite.objects.filter(user=self.groupless_user, group=self.group_no_direct).exists())

    def test_group_request_invite_accept(self):
        self.group_join(self.groupless_user, self.group_no_direct)

        factory = APIRequestFactory()
        user = self.group_no_direct_user_creator.user
        view = GroupInviteAcceptApi.as_view()
        request = factory.post('', data=dict(to=self.groupless_user.id))
        force_authenticate(request, user)
        view(request, group=self.group_no_direct.id)

        self.assertTrue(GroupUser.objects.filter(user_id=self.groupless_user, group=self.group_no_direct).exists())

    def test_group_request_invite_accept_no_invite(self):
        factory = APIRequestFactory()
        user = self.group_no_direct_user_creator.user
        view = GroupInviteAcceptApi.as_view()
        request = factory.post('', data=dict(to=self.groupless_user.id))
        force_authenticate(request, user)
        view(request, group=self.group_no_direct.id)

        self.assertFalse(GroupUser.objects.filter(user_id=self.groupless_user, group=self.group_no_direct).exists())

    def test_user_invite_list(self):
        self.group_invite(self.group_no_direct_user_creator, self.groupless_user)
        self.group_invite(self.group_private_user_creator, self.groupless_user)

        factory = APIRequestFactory()
        user = self.groupless_user
        view = GroupInviteListApi.as_view()

        request = factory.get('', data=dict(limit=10))
        force_authenticate(request, user=user)
        response = view(request)

        pprint(response.data)

    def test_user_group_join_request_list(self):
        self.group_join(self.groupless_user, self.group_no_direct)
        self.group_join(self.groupless_user, self.group_private)

        for group_user, allowed in [(self.group_private_user_creator, False),
                                    (self.group_no_direct_user_creator, True)]:
            factory = APIRequestFactory()
            user = group_user.user
            view = GroupInviteListApi.as_view()

            request = factory.get('', data=dict(limit=10))
            force_authenticate(request, user=user)
            response = view(request, group=group_user.group)

            self.assertTrue(bool(response.data.get('results')) == allowed)
