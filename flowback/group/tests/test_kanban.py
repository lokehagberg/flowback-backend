from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.group.tests.factories import GroupFactory, WorkGroupFactory, WorkGroupUserFactory
from flowback.kanban.tests.factories import KanbanEntryFactory
from flowback.user.views.kanban import UserKanbanEntryListAPI


class TestKanban(APITestCase):
    def setUp(self):
        self.group_one = GroupFactory()
        self.group_two = GroupFactory()

        self.workgroup_one = WorkGroupFactory(group=self.group_one)
        self.workgroup_two = WorkGroupFactory(group=self.group_two)

        self.group_user_one = self.group_one.group_user_creator
        self.group_user_two = self.group_two.group_user_creator

        self.workgroupuser_one = WorkGroupUserFactory(group_user=self.group_user_one, work_group=self.workgroup_one)
        self.workgroupuser_two = WorkGroupUserFactory(group_user=self.group_user_two, work_group=self.workgroup_two)

    def test_kanban_list(self):
        kanbanentrieswg_one = KanbanEntryFactory.create_batch(2,
                                                              work_group=self.workgroup_one,
                                                              kanban=self.group_one.kanban)
        kanbanentrieswg_two = KanbanEntryFactory.create_batch(6,
                                                              work_group=self.workgroup_two,
                                                              kanban=self.group_two.kanban)

        kanbanentriesg_one = KanbanEntryFactory.create_batch(3,
                                                             kanban=self.group_one.kanban)
        kanbanentriesg_two = KanbanEntryFactory.create_batch(3,
                                                             kanban=self.group_two.kanban,
                                                             assignee=self.group_user_two.user)

        kanbanentriesu_one = KanbanEntryFactory.create_batch(5, kanban=self.group_user_one.user.kanban)
        kanbanentriesu_two = KanbanEntryFactory.create_batch(9, kanban=self.group_user_two.user.kanban)

        response = generate_request(api=UserKanbanEntryListAPI, user=self.group_user_one.user)
        self.assertEqual(response.data['count'], 10)

        response = generate_request(api=UserKanbanEntryListAPI, user=self.group_user_two.user)
        self.assertEqual(response.data['count'], 18)

        response = generate_request(api=UserKanbanEntryListAPI,
                                    user=self.group_user_two.user,
                                    data={'assignee': self.group_user_two.user.id})

        self.assertEqual(response.data['count'], 3)

        response = generate_request(api=UserKanbanEntryListAPI,
                                    user=self.group_user_two.user,
                                    data={'title__icontains': kanbanentriesg_two[0].title})

        self.assertEqual(response.data['count'], 1)
