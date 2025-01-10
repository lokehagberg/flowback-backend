from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.group.models import GroupThreadVote
from flowback.group.tests.factories import GroupThreadFactory, GroupUserFactory, GroupThreadVoteFactory
from flowback.group.views.thread import GroupThreadVoteUpdateAPI, GroupThreadListAPI
from flowback.user.models import User


class TestGroupThread(APITestCase):
    def setUp(self):
        self.group_admin = GroupUserFactory()
        self.threads = GroupThreadFactory.create_batch(10, created_by=self.group_admin)
        self.group_user = GroupUserFactory(group=self.group_admin.group)

    def test_list(self):
        user = self.group_user.user

        # Create votes to see user votes
        GroupThreadVoteFactory.create(created_by=self.group_user, thread=self.threads[0], vote=True)

        # Thread no.5 should have a score of 2
        GroupThreadVoteFactory.create(created_by=self.group_user, thread=self.threads[4], vote=True)
        GroupThreadVoteFactory.create(thread=self.threads[4], vote=True)
        GroupThreadVoteFactory.create(thread=self.threads[4], vote=True)
        GroupThreadVoteFactory.create(thread=self.threads[4], vote=False)

        GroupThreadVoteFactory.create(created_by=self.group_user, thread=self.threads[5], vote=False)

        response = generate_request(api=GroupThreadListAPI,
                                    url_params=dict(group_id=self.group_user.group.id),
                                    user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 10)

        # Check user vote and score against expected values
        self.assertTrue(response.data['results'][0]['user_vote'])
        self.assertEqual(response.data['results'][0]['score'], 1)

        self.assertTrue(response.data['results'][4]['user_vote'])
        self.assertEqual(response.data['results'][4]['score'], 2)

        self.assertFalse(response.data['results'][5]['user_vote'])
        self.assertEqual(response.data['results'][5]['score'], -1)

        for n in [1, 2, 3, 6, 7, 8, 9]:
            self.assertIsNone(response.data['results'][n]['user_vote'])
            self.assertEqual(response.data['results'][n]['score'], 0)


class TestGroupThreadVote(APITestCase):
    def setUp(self):
        self.group_admin = GroupUserFactory()
        self.threads = GroupThreadFactory.create_batch(10, created_by=self.group_admin)
        self.group_user = GroupUserFactory(group=self.group_admin.group)

    @staticmethod
    def vote(thread_id: int, user: User, val: bool = None):
        return generate_request(api=GroupThreadVoteUpdateAPI,
                                data=dict(vote=val) if val is not None else None,
                                url_params=dict(thread_id=thread_id),
                                user=user)

    def test_vote(self):
        thread_id = self.threads[0].id
        user = self.group_user.user

        # Vote is True
        response = self.vote(thread_id, user, True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vote = GroupThreadVote.objects.get(thread_id=thread_id, created_by=self.group_user)

        # Vote is False
        response = self.vote(thread_id, user, False)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vote = GroupThreadVote.objects.get(thread_id=thread_id, created_by=self.group_user)

        # Vote is None
        response = self.vote(thread_id, user, None)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertRaises(GroupThreadVote.DoesNotExist):
            GroupThreadVote.objects.get(thread_id=thread_id, created_by=self.group_user)

        # Vote is None and still cast None
        response = self.vote(thread_id, user, None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
