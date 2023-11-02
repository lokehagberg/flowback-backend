import json
import random

from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from .factories import PollFactory
from ..views.poll import PollListApi
from ...files.tests.factories import FileSegmentFactory
from ...group.tests.factories import GroupFactory, GroupUserFactory


class PollTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = GroupUserFactory(group=self.group)
        (self.poll_one,
         self.poll_two,
         self.poll_three) = [PollFactory(created_by=self.group_user_creator) for x in range(3)]
        segment = FileSegmentFactory()
        self.poll_three.attachments = segment.collection
        self.poll_three.save()

    def test_list_polls(self):
        factory = APIRequestFactory()
        user = self.group_user_creator.user
        view = PollListApi.as_view()

        request = factory.get('')
        force_authenticate(request, user)
        response = view(request, group_id=self.group.id)

        print(json.loads(response.rendered_content))
