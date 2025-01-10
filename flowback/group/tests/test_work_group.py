
import json
from pprint import pprint

from rest_framework import status
from rest_framework.test import APITransactionTestCase

from flowback.common.tests import generate_request
from flowback.group.models import WorkGroup, WorkGroupUser, WorkGroupUserJoinRequest
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, WorkGroupUserFactory, WorkGroupFactory, \
    WorkGroupJoinRequestFactory
from flowback.group.views.group import WorkGroupCreateAPI, WorkGroupUpdateAPI, \
    WorkGroupDeleteAPI, WorkGroupUserJoinAPI, WorkGroupUserLeaveAPI, WorkGroupUserAddAPI, WorkGroupUserListAPI, \
    WorkGroupUserJoinRequestListAPI, WorkGroupListAPI, WorkGroupUserUpdateAPI
from flowback.user.tests.factories import UserFactory


class WorkGroupTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        (self.group_one,
         self.group_two,
         self.group_three) = [GroupFactory.create(public=True) for x in range(3)]

        (self.group_user_creator_one,
         self.group_user_creator_two,
         self.group_user_creator_three) = [GroupUserFactory.create(group=group, user=group.created_by
                                                                   ) for group in [self.group_one,
                                                                                   self.group_two,
                                                                                   self.group_three]]

        self.group_no_direct = GroupFactory.create(public=True, direct_join=False)
        self.group_no_direct_user_creator = GroupUserFactory.create(group=self.group_no_direct,
                                                                    user=self.group_no_direct.created_by)

        self.group_private = GroupFactory.create(public=False)
        self.group_private_user_creator = GroupUserFactory.create(group=self.group_private,
                                                                  user=self.group_private.created_by)

        self.groupless_user = UserFactory()

    # Work Group Test
    def test_work_group_list(self):
        work_group_one = WorkGroupFactory(group=self.group_user_creator_one.group)
        work_group_two = WorkGroupFactory(group=self.group_user_creator_one.group)

        # Irrelevant work group, for testing purpose
        WorkGroupFactory(group=self.group_user_creator_two.group)

        response = generate_request(api=WorkGroupListAPI,
                                    user=self.group_user_creator_one.user,
                                    url_params=dict(group_id=self.group_user_creator_one.group.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], work_group_one.id)
        self.assertEqual(response.data['results'][1]['id'], work_group_two.id)


    def test_work_group_user_list(self):
        work_group_one = WorkGroupFactory(group=self.group_user_creator_one.group)
        work_group_two = WorkGroupFactory(group=self.group_user_creator_one.group)
        work_group_user_one = WorkGroupUserFactory(group_user__group=self.group_user_creator_one.group,
                                                   work_group=work_group_one)
        work_group_user_two = WorkGroupUserFactory(group_user__group=self.group_user_creator_one.group,
                                                   work_group=work_group_one)

        # Irrelevant work group user, for testing purpose
        WorkGroupUserFactory(group_user__group=self.group_user_creator_one.group, work_group=work_group_two)

        response = generate_request(api=WorkGroupUserListAPI,
                                    user=self.group_user_creator_one.user,
                                    url_params=dict(work_group_id=work_group_one.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['group_user']['user']['id'],
                         work_group_user_one.group_user.user.id)
        self.assertEqual(response.data['results'][1]['group_user']['user']['id'],
                         work_group_user_two.group_user.user.id)


    def test_work_group_user_join_request_list(self):
        work_group_one = WorkGroupFactory(group=self.group_user_creator_one.group)
        work_group_two = WorkGroupFactory(group=self.group_user_creator_one.group)
        work_group_user_one = WorkGroupUserFactory(group_user__group=self.group_user_creator_one.group,
                                                   work_group=work_group_one)
        WorkGroupUserFactory(group_user__group=self.group_user_creator_one.group, work_group=work_group_one)

        # Join Request
        join_request = WorkGroupJoinRequestFactory(group_user__group=self.group_user_creator_one.group,
                                                   work_group=work_group_one)

        # Irrelevant work group user, for testing purpose
        WorkGroupUserFactory(group_user__group=self.group_user_creator_one.group, work_group=work_group_two)
        WorkGroupJoinRequestFactory(group_user__group=self.group_user_creator_one.group, work_group=work_group_two)

        response = generate_request(api=WorkGroupUserJoinRequestListAPI,
                                    user=work_group_user_one.group_user.user,
                                    url_params=dict(work_group_id=work_group_one.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['group_user']['user']['id'],
                         join_request.group_user.user.id)


    def test_work_group_create(self):
        data = dict(name="test_work_group", direct_join=True)

        response = generate_request(api=WorkGroupCreateAPI,
                                    data=data,
                                    url_params=dict(group_id=self.group_user_creator_one.group.id),
                                    user=self.group_user_creator_one.user)

        work_group = WorkGroup.objects.get(id=response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(work_group.name, data['name'])
        self.assertEqual(work_group.group, self.group_user_creator_one.group)
        self.assertEqual(work_group.direct_join, data['direct_join'])


    def test_work_group_update(self):
        work_group = WorkGroupFactory(group=self.group_user_creator_one.group, name="test_old", direct_join=False)
        data = dict(name="test_updated", direct_join=True)

        response = generate_request(api=WorkGroupUpdateAPI,
                                    data=data,
                                    url_params=dict(work_group_id=work_group.id),
                                    user=self.group_user_creator_one.user)

        work_group.refresh_from_db()
        self.assertTrue(response.status_code == status.HTTP_204_NO_CONTENT)
        self.assertEqual(work_group.name, data['name'])
        self.assertEqual(work_group.direct_join, data['direct_join'])


    def test_work_group_delete(self):
        work_group = WorkGroupFactory(group=self.group_user_creator_one.group, name="test_old", direct_join=False)

        response = generate_request(api=WorkGroupDeleteAPI,
                                    url_params=dict(work_group_id=work_group.id),
                                    user=self.group_user_creator_one.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkGroup.objects.filter(id=work_group.id).exists())


    # Work Group User Test
    def test_work_group_user_join(self):
        work_group = WorkGroupFactory(group=self.group_user_creator_one.group, direct_join=True)

        response = generate_request(api=WorkGroupUserJoinAPI,
                                    url_params=dict(work_group_id=work_group.id),
                                    user=self.group_user_creator_one.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(WorkGroupUser.objects.filter(id=work_group.id).exists())


    def test_work_group_user_leave(self):
        work_group_user = WorkGroupUserFactory(group_user=self.group_user_creator_one)

        response = generate_request(api=WorkGroupUserLeaveAPI,
                                    url_params=dict(work_group_id=work_group_user.work_group.id),
                                    user=self.group_user_creator_one.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkGroupUser.objects.filter(id=work_group_user.work_group.id).exists())


    def test_work_group_user_invite(self):
        group_user = GroupUserFactory(group=self.group_user_creator_one.group)
        work_group = WorkGroupFactory(group=self.group_user_creator_one.group, direct_join=False)
        work_group_user = WorkGroupUserFactory(group_user=GroupUserFactory(group=self.group_user_creator_one.group,
                                                                           is_admin=False),
                                               work_group=work_group,
                                               is_moderator=True)

        response = generate_request(api=WorkGroupUserJoinAPI,
                                    url_params=dict(work_group_id=work_group.id),
                                    user=group_user.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertFalse(WorkGroupUser.objects.filter(group_user=group_user, work_group=work_group).exists())
        self.assertTrue(WorkGroupUserJoinRequest.objects.filter(group_user=group_user, work_group=work_group).exists())

        # Accept join request
        response = generate_request(api=WorkGroupUserAddAPI,
                                    url_params=dict(work_group_id=work_group.id),
                                    data=dict(target_group_user_id=group_user.id, is_moderator=False),
                                    user=work_group_user.group_user.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(WorkGroupUser.objects.filter(group_user=group_user, work_group=work_group).exists())
        self.assertFalse(WorkGroupUserJoinRequest.objects.filter(group_user=group_user, work_group=work_group).exists())


    def test_work_group_user_direct_join(self):
        group_user = GroupUserFactory(group=self.group_user_creator_one.group)
        work_group = WorkGroupFactory(group=self.group_user_creator_one.group, direct_join=True)

        response = generate_request(api=WorkGroupUserJoinAPI,
                                    url_params=dict(work_group_id=work_group.id),
                                    user=group_user.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(WorkGroupUser.objects.filter(group_user=group_user, work_group=work_group).exists())


    def test_work_group_user_update(self):
        group_user = GroupUserFactory(group=self.group_user_creator_one.group)
        work_group = WorkGroupFactory(group=self.group_user_creator_one.group, direct_join=False)
        work_group_user = WorkGroupUserFactory(group_user=GroupUserFactory(group=self.group_user_creator_one.group,
                                                                           is_admin=False),
                                               work_group=work_group,
                                               is_moderator=True)

        target_work_group_user = WorkGroupUserFactory(
            group_user=GroupUserFactory(
                group=self.group_user_creator_one.group,
                is_admin=False),
            work_group=work_group,
            is_moderator=False)

        response = generate_request(api=WorkGroupUserUpdateAPI,
                                    url_params=dict(work_group_id=work_group.id),
                                    data=dict(target_group_user_id=target_work_group_user.group_user.id,
                                              is_moderator=True),
                                    user=work_group_user.group_user.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertTrue(WorkGroupUser.objects.get(group_user=target_work_group_user.group_user,
                                                  work_group=work_group).is_moderator)
