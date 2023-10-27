import json
from pprint import pprint

from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase

from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.group.views.group import GroupListApi


class GroupTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        (self.group_one,
         self.group_two,
         self.group_three,
         self.group_four,
         self.group_five) = [GroupFactory.create(public=True) for x in range(5)]

        (self.group_user_creator_one,
         self.group_user_creator_two,
         self.group_user_creator_three,
         self.group_user_creator_four,
         self.group_user_creator_five) = [GroupUserFactory.create(group=group,
                                                                  user=group.created_by) for group in [self.group_one,
                                                                                                       self.group_two,
                                                                                                       self.group_three,
                                                                                                       self.group_four,
                                                                                                       self.group_five]]

    def test_group_list(self):
        factory = APIRequestFactory()
        user = self.group_user_creator_two.user
        view = GroupListApi.as_view()

        request = factory.get('', data=dict(limit=10))
        force_authenticate(request, user=user)
        response = view(request)

        data = json.loads(response.rendered_content)
        pprint(data)
