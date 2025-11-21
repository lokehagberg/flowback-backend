from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.group.tests.factories import (GroupFactory, GroupUserFactory, WorkGroupFactory,
                                            WorkGroupUserFactory, GroupPermissionsFactory)
from flowback.group.views.schedule import (GroupScheduleEventCreateAPI, GroupScheduleEventUpdateAPI,
                                           GroupScheduleEventDeleteAPI, WorkGroupScheduleEventCreateAPI,
                                           WorkGroupScheduleEventUpdateAPI, WorkGroupScheduleEventDeleteAPI)
from flowback.schedule.models import ScheduleEvent, ScheduleEventSubscription, ScheduleUser
from flowback.schedule.tests.factories import ScheduleEventFactory, ScheduleUserFactory
from flowback.schedule.views import ScheduleEventSubscribeAPI, ScheduleEventUnsubscribeAPI
from flowback.user.tests.factories import UserFactory


class TestGroupSchedule(APITestCase):
    """Test Group schedule event create, update, delete operations"""

    def setUp(self):
        # Create group with admin user
        self.group = GroupFactory()
        self.admin_user = self.group.created_by
        self.admin_group_user = self.group.group_user_creator

        # Create user with schedule_event_create permission
        self.user_with_create_perm = UserFactory()
        self.group_user_with_create = GroupUserFactory(
            user=self.user_with_create_perm,
            group=self.group,
            is_admin=False,
            permission=GroupPermissionsFactory(schedule_event_create=True,
                                               schedule_event_update=False,
                                               schedule_event_delete=False)
        )

        # Create user with schedule_event_update permission
        self.user_with_update_perm = UserFactory()
        self.group_user_with_update = GroupUserFactory(
            user=self.user_with_update_perm,
            group=self.group,
            is_admin=False,
            permission=GroupPermissionsFactory(schedule_event_create=False,
                                               schedule_event_update=True,
                                               schedule_event_delete=False)
        )

        # Create user with schedule_event_delete permission
        self.user_with_delete_perm = UserFactory()
        self.group_user_with_delete = GroupUserFactory(
            user=self.user_with_delete_perm,
            group=self.group,
            is_admin=False,
            permission=GroupPermissionsFactory(schedule_event_create=False,
                                               schedule_event_update=False,
                                               schedule_event_delete=True)
        )

        # Create user without any schedule permissions
        self.unprivileged_user = UserFactory()
        self.unprivileged_group_user = GroupUserFactory(
            user=self.unprivileged_user,
            group=self.group,
            is_admin=False,
            permission=GroupPermissionsFactory(schedule_event_create=False,
                                               schedule_event_update=False,
                                               schedule_event_delete=False)
        )

    def test_group_schedule_event_create_as_admin(self):
        """Admin can create schedule events"""
        data = {
            'title': 'Test Event',
            'description': 'Test Description',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'end_date': (timezone.now() + timedelta(days=1, hours=2)).isoformat(),
            'tag': 'meeting',
            'meeting_link': 'https://example.com/meeting'
        }

        response = generate_request(api=GroupScheduleEventCreateAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ScheduleEvent.objects.filter(title='Test Event',
                                                     schedule=self.group.schedule).exists())

    def test_group_schedule_event_create_with_permission(self):
        """User with schedule_event_create permission can create events"""
        data = {
            'title': 'Event by Permitted User',
            'description': 'Created by user with permission',
            'start_date': (timezone.now() + timedelta(days=2)).isoformat(),
            'end_date': (timezone.now() + timedelta(days=2, hours=1)).isoformat()
        }

        response = generate_request(api=GroupScheduleEventCreateAPI,
                                    user=self.user_with_create_perm,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ScheduleEvent.objects.filter(title='Event by Permitted User').exists())

    def test_group_schedule_event_create_without_permission(self):
        """User without schedule_event_create permission cannot create events"""
        data = {
            'title': 'Unauthorized Event',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat()
        }

        response = generate_request(api=GroupScheduleEventCreateAPI,
                                    user=self.unprivileged_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 403)

    def test_group_schedule_event_create_unauthorized_user(self):
        """User not in the group cannot create events"""
        unauthorized_user = UserFactory()
        data = {
            'title': 'Unauthorized Event',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat()
        }

        response = generate_request(api=GroupScheduleEventCreateAPI,
                                    user=unauthorized_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 404)

    def test_group_schedule_event_create_missing_required_fields(self):
        """Creating event without required fields fails validation"""
        data = {
            'description': 'Missing title and start_date'
        }

        response = generate_request(api=GroupScheduleEventCreateAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 400)

    def test_group_schedule_event_update_as_admin(self):
        """Admin can update schedule events"""
        event = ScheduleEventFactory(schedule=self.group.schedule,
                                     title='Original Title',
                                     description='Original Description')

        data = {
            'event_id': event.id,
            'title': 'Updated Title',
            'description': 'Updated Description'
        }

        response = generate_request(api=GroupScheduleEventUpdateAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        updated_event = ScheduleEvent.objects.get(id=event.id)
        self.assertEqual(updated_event.title, 'Updated Title')
        self.assertEqual(updated_event.description, 'Updated Description')

    def test_group_schedule_event_update_with_permission(self):
        """User with schedule_event_update permission can update events"""
        event = ScheduleEventFactory(schedule=self.group.schedule, title='Original')

        data = {
            'event_id': event.id,
            'title': 'Updated by Permitted User'
        }

        response = generate_request(api=GroupScheduleEventUpdateAPI,
                                    user=self.user_with_update_perm,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        updated_event = ScheduleEvent.objects.get(id=event.id)
        self.assertEqual(updated_event.title, 'Updated by Permitted User')

    def test_group_schedule_event_update_without_permission(self):
        """User without schedule_event_update permission cannot update events"""
        event = ScheduleEventFactory(schedule=self.group.schedule)

        data = {
            'event_id': event.id,
            'title': 'Unauthorized Update'
        }

        response = generate_request(api=GroupScheduleEventUpdateAPI,
                                    user=self.unprivileged_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 403)

    def test_group_schedule_event_update_nonexistent_event(self):
        """Updating nonexistent event raises exception"""
        data = {
            'event_id': 99999,
            'title': 'Should Fail'
        }

        response = generate_request(api=GroupScheduleEventUpdateAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))
        self.assertEqual(response.status_code, 404)

    def test_group_schedule_event_delete_as_admin(self):
        """Admin can delete schedule events"""
        event = ScheduleEventFactory(schedule=self.group.schedule)
        event_id = event.id

        data = {'event_id': event.id}

        response = generate_request(api=GroupScheduleEventDeleteAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScheduleEvent.objects.filter(id=event_id).exists())

    def test_group_schedule_event_delete_with_permission(self):
        """User with schedule_event_delete permission can delete events"""
        event = ScheduleEventFactory(schedule=self.group.schedule)
        event_id = event.id

        data = {'event_id': event.id}

        response = generate_request(api=GroupScheduleEventDeleteAPI,
                                    user=self.user_with_delete_perm,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScheduleEvent.objects.filter(id=event_id).exists())

    def test_group_schedule_event_delete_without_permission(self):
        """User without schedule_event_delete permission cannot delete events"""
        event = ScheduleEventFactory(schedule=self.group.schedule)

        data = {'event_id': event.id}

        response = generate_request(api=GroupScheduleEventDeleteAPI,
                                    user=self.unprivileged_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 403)

    def test_group_schedule_event_delete_nonexistent_event(self):
        """Deleting nonexistent event raises exception"""
        data = {'event_id': 99999}

        response = generate_request(api=GroupScheduleEventDeleteAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 404)


class TestWorkGroupSchedule(APITestCase):
    """Test WorkGroup schedule event create, update, delete operations"""

    def setUp(self):
        # Create group and workgroup
        self.group = GroupFactory()
        self.admin_user = self.group.created_by
        self.admin_group_user = self.group.group_user_creator

        self.work_group = WorkGroupFactory(group=self.group)

        # Create workgroup moderator
        self.moderator_user = UserFactory()
        self.moderator_group_user = GroupUserFactory(
            user=self.moderator_user,
            group=self.group,
            is_admin=False
        )
        self.moderator_work_group_user = WorkGroupUserFactory(
            work_group=self.work_group,
            group_user=self.moderator_group_user,
            is_moderator=True
        )

        # Create regular workgroup member
        self.member_user = UserFactory()
        self.member_group_user = GroupUserFactory(
            user=self.member_user,
            group=self.group,
            is_admin=False
        )
        self.member_work_group_user = WorkGroupUserFactory(
            work_group=self.work_group,
            group_user=self.member_group_user,
            is_moderator=False
        )

        # Create user not in workgroup
        self.non_member_user = UserFactory()
        self.non_member_group_user = GroupUserFactory(
            user=self.non_member_user,
            group=self.group,
            is_admin=False
        )

    def test_workgroup_schedule_event_create_as_admin(self):
        """Group admin can create workgroup schedule events"""
        data = {
            'title': 'WorkGroup Event',
            'description': 'WorkGroup meeting',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'end_date': (timezone.now() + timedelta(days=1, hours=1)).isoformat()
        }

        response = generate_request(api=WorkGroupScheduleEventCreateAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ScheduleEvent.objects.filter(title='WorkGroup Event',
                                                     schedule=self.work_group.schedule).exists())

    def test_workgroup_schedule_event_create_as_moderator(self):
        """WorkGroup moderator can create schedule events"""
        data = {
            'title': 'Moderator Event',
            'start_date': (timezone.now() + timedelta(days=2)).isoformat()
        }

        response = generate_request(api=WorkGroupScheduleEventCreateAPI,
                                    user=self.moderator_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ScheduleEvent.objects.filter(title='Moderator Event').exists())

    def test_workgroup_schedule_event_create_as_member(self):
        """Regular workgroup member cannot create schedule events"""
        data = {
            'title': 'Member Event',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat()
        }

        response = generate_request(api=WorkGroupScheduleEventCreateAPI,
                                    user=self.member_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 403)

    def test_workgroup_schedule_event_create_as_non_member(self):
        """User not in workgroup cannot create schedule events"""
        data = {
            'title': 'Non-Member Event',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat()
        }

        response = generate_request(api=WorkGroupScheduleEventCreateAPI,
                                    user=self.non_member_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 403)

    def test_workgroup_schedule_event_update_as_admin(self):
        """Group admin can update workgroup schedule events"""
        event = ScheduleEventFactory(schedule=self.work_group.schedule, title='Original')

        data = {
            'event_id': event.id,
            'title': 'Updated by Admin'
        }

        response = generate_request(api=WorkGroupScheduleEventUpdateAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 200)
        updated_event = ScheduleEvent.objects.get(id=event.id)
        self.assertEqual(updated_event.title, 'Updated by Admin')

    def test_workgroup_schedule_event_update_as_moderator(self):
        """WorkGroup moderator can update schedule events"""
        event = ScheduleEventFactory(schedule=self.work_group.schedule, title='Original')

        data = {
            'event_id': event.id,
            'title': 'Updated by Moderator'
        }

        response = generate_request(api=WorkGroupScheduleEventUpdateAPI,
                                    user=self.moderator_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 200)
        updated_event = ScheduleEvent.objects.get(id=event.id)
        self.assertEqual(updated_event.title, 'Updated by Moderator')

    def test_workgroup_schedule_event_update_as_member(self):
        """Regular workgroup member cannot update schedule events"""
        event = ScheduleEventFactory(schedule=self.work_group.schedule)

        data = {
            'event_id': event.id,
            'title': 'Unauthorized Update'
        }

        response = generate_request(api=WorkGroupScheduleEventUpdateAPI,
                                    user=self.member_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 403)

    def test_workgroup_schedule_event_delete_as_admin(self):
        """Group admin can delete workgroup schedule events"""
        event = ScheduleEventFactory(schedule=self.work_group.schedule)
        event_id = event.id

        data = {'event_id': event.id}

        response = generate_request(api=WorkGroupScheduleEventDeleteAPI,
                                    user=self.admin_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScheduleEvent.objects.filter(id=event_id).exists())

    def test_workgroup_schedule_event_delete_as_moderator(self):
        """WorkGroup moderator can delete schedule events"""
        event = ScheduleEventFactory(schedule=self.work_group.schedule)
        event_id = event.id

        data = {'event_id': event.id}

        response = generate_request(api=WorkGroupScheduleEventDeleteAPI,
                                    user=self.moderator_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScheduleEvent.objects.filter(id=event_id).exists())

    def test_workgroup_schedule_event_delete_as_member(self):
        """Regular workgroup member cannot delete schedule events"""
        event = ScheduleEventFactory(schedule=self.work_group.schedule)

        data = {'event_id': event.id}

        response = generate_request(api=WorkGroupScheduleEventDeleteAPI,
                                    user=self.member_user,
                                    data=data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 403)


class TestScheduleIntegration(APITestCase):
    """Test schedule view integration and subscription functionality"""

    def setUp(self):
        # Create group with admin
        self.group = GroupFactory()
        self.admin_user = self.group.created_by
        self.admin_group_user = self.group.group_user_creator

        # Create regular user
        self.user = UserFactory()
        self.group_user = GroupUserFactory(user=self.user, group=self.group, is_admin=False)

        # Create workgroup
        self.work_group = WorkGroupFactory(group=self.group)
        self.work_group_user = WorkGroupUserFactory(
            work_group=self.work_group,
            group_user=self.group_user
        )

    def test_group_schedule_event_appears_in_schedule(self):
        """Created group schedule events should appear in the group's schedule"""
        # Create event
        event_data = {
            'title': 'Group Meeting',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat()
        }

        response = generate_request(api=GroupScheduleEventCreateAPI,
                                    user=self.admin_user,
                                    data=event_data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)

        # Verify event is in group schedule
        events = ScheduleEvent.objects.filter(schedule=self.group.schedule, title='Group Meeting')
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().schedule.id, self.group.schedule.id)

    def test_workgroup_schedule_event_appears_in_workgroup_schedule(self):
        """Created workgroup schedule events should appear in the workgroup's schedule"""
        event_data = {
            'title': 'WorkGroup Meeting',
            'start_date': (timezone.now() + timedelta(days=1)).isoformat()
        }

        response = generate_request(api=WorkGroupScheduleEventCreateAPI,
                                    user=self.admin_user,
                                    data=event_data,
                                    url_params=dict(work_group_id=self.work_group.id))

        self.assertEqual(response.status_code, 200)

        # Verify event is in workgroup schedule
        events = ScheduleEvent.objects.filter(schedule=self.work_group.schedule, title='WorkGroup Meeting')
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().schedule.id, self.work_group.schedule.id)

    def test_event_subscription(self):
        """Users can subscribe to schedule events"""
        # Create an event
        event = ScheduleEventFactory(schedule=self.group.schedule, title='Subscribable Event')

        # Subscribe to the event
        subscription_data = {
            'event_ids': str(event.id),
            'locked': True
        }

        response = generate_request(api=ScheduleEventSubscribeAPI,
                                    user=self.user,
                                    data=subscription_data,
                                    url_params=dict(schedule_id=self.group.schedule.id))

        self.assertEqual(response.status_code, 200)

        # Verify subscription exists
        self.assertTrue(
            ScheduleEventSubscription.objects.filter(
                event=event,
                schedule_user__user=self.user
            ).exists()
        )

    def test_event_unsubscription(self):
        """Users can unsubscribe from schedule events"""
        # Create event and subscription
        event = ScheduleEventFactory(schedule=self.group.schedule)
        subscription = ScheduleEventSubscription.objects.create(
            event=event,
            schedule_user=ScheduleUser.objects.get(user=self.user, schedule=self.group.schedule),
            locked=True
        )

        # Unsubscribe from the event
        unsubscription_data = {
            'event_ids': str(event.id)
        }

        response = generate_request(api=ScheduleEventUnsubscribeAPI,
                                    user=self.user,
                                    data=unsubscription_data,
                                    url_params=dict(schedule_id=self.group.schedule.id))

        self.assertEqual(response.status_code, 200)

        # Verify subscription is removed
        self.assertFalse(
            ScheduleEventSubscription.objects.filter(
                event=event,
                schedule_user__user=self.user
            ).exists()
        )

    def test_multiple_events_in_group_schedule(self):
        """Multiple events can be created and tracked in group schedule"""
        events_data = [
            {'title': 'Event 1', 'start_date': (timezone.now() + timedelta(days=1)).isoformat()},
            {'title': 'Event 2', 'start_date': (timezone.now() + timedelta(days=2)).isoformat()},
            {'title': 'Event 3', 'start_date': (timezone.now() + timedelta(days=3)).isoformat()}
        ]

        for event_data in events_data:
            response = generate_request(api=GroupScheduleEventCreateAPI,
                                        user=self.admin_user,
                                        data=event_data,
                                        url_params=dict(group_id=self.group.id))
            self.assertEqual(response.status_code, 200)

        # Verify all events exist in schedule
        events_count = ScheduleEvent.objects.filter(schedule=self.group.schedule).count()
        self.assertEqual(events_count, 3)

    def test_updated_event_maintains_schedule_association(self):
        """Updated events remain associated with their original schedule"""
        event = ScheduleEventFactory(schedule=self.group.schedule, title='Original Title')
        original_schedule_id = event.schedule.id

        update_data = {
            'event_id': event.id,
            'title': 'Updated Title'
        }

        response = generate_request(api=GroupScheduleEventUpdateAPI,
                                    user=self.admin_user,
                                    data=update_data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)

        # Verify schedule association is maintained
        updated_event = ScheduleEvent.objects.get(id=event.id)
        self.assertEqual(updated_event.schedule.id, original_schedule_id)
        self.assertEqual(updated_event.title, 'Updated Title')
