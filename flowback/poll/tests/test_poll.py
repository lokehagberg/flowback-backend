from datetime import datetime, timedelta, timezone

from django.test import TestCase
from flowback.user.models import User
from flowback.group.models import GroupUser, GroupUserDelegatePool
from flowback.group.services import (group_user_permissions,
                                     group_user_delegate,
                                     group_permission_create,
                                     group_create,
                                     group_update,
                                     group_join,
                                     group_user_update,
                                     group_user_delegate_pool_create,
                                     group_tag_create)
from flowback.common.services import get_object
from flowback.poll.services import (poll_create,
                                    poll_update,
                                    poll_delete,
                                    poll_refresh,
                                    poll_finish,
                                    poll_refresh_cheap,
                                    poll_proposal_create,
                                    poll_proposal_delete,
                                    poll_proposal_vote_count,
                                    poll_proposal_vote_update)
from flowback.poll.models import (Poll, PollProposal, PollVoting, PollDelegateVoting, PollVotingTypeRanking)


# Create your tests here.
class GroupDelegationTests(TestCase):
    def setUp(self):
        self.user_creator = User.objects.create_superuser(username='user_creator',
                                                          email='creator@example.com',
                                                          password='password123')
        self.user_delegate = User.objects.create_user(username='user_delegate',
                                                      email='member@example.com',
                                                      password='password123')
        self.user_delegator = User.objects.create_user(username='user_delegator',
                                                       email='member_2@example.com',
                                                       password='password123')
        self.user_non_delegate = User.objects.create_user(username='user_non_delegate',
                                                          email='member_3@example.com',
                                                          password='password123')
        self.user_non_member = User.objects.create_user(username='user_non_member',
                                                        email='member_4@example.com',
                                                        password='password123')
        self.group = group_create(user=self.user_creator.id,
                                  name='test_group',
                                  description='desc',
                                  image='image',
                                  cover_image='cover_image',
                                  public=True,
                                  direct_join=True)

        permission = group_permission_create(user=self.user_creator.id, group=self.group.id, role_name='Member',
                                             invite_user=False, create_poll=True, allow_vote=True,
                                             kick_members=False, ban_members=False)
        group_update(user=self.user_creator.id, group=self.group.id, data=dict(default_permission=permission.id))



        self.user_non_delegate = group_join(user=self.user_non_delegate.id, group=self.group.id)
        self.user_creator = get_object(GroupUser, user=self.user_creator, group=self.group)

        self.tag_one = group_tag_create(user=self.user_creator.user.id, group=self.group.id, tag_name='tag_one')
        self.tag_two = group_tag_create(user=self.user_creator.user.id, group=self.group.id, tag_name='tag_two')
        self.tag_three = group_tag_create(user=self.user_creator.user.id, group=self.group.id, tag_name='tag_three')

        self.user_delegator = group_join(user=self.user_delegator.id, group=self.group.id)
        self.user_delegate = group_join(user=self.user_delegate.id, group=self.group.id)
        self.user_delegate_pool = group_user_delegate_pool_create(user=self.user_delegate.user.id, group=self.group.id)

        self.delegate_pool = GroupUserDelegatePool.objects.get(groupuserdelegate__group_user=self.user_delegate)

        self.delegate_rel = group_user_delegate(user=self.user_delegate.user.id, group=self.group.id,
                                                delegate_pool_id=self.delegate_pool.id, tags=[self.tag_one.id])

    def generate_poll(self, title: str = 'test_poll', description: str = 'test_description') -> Poll:
        return Poll.objects.create(created_by=self.user_creator,
                                   title=title, description=description,
                                   start_date=datetime.now(tz=timezone.utc),
                                   end_date=datetime.now(tz=timezone.utc) + timedelta(hours=2),
                                   poll_type=1, tag=self.tag_one, dynamic=True)

    def generate_proposal(self, poll_id: int, title: str = 'test_poll', description: str = 'test_description') -> PollProposal:
        return PollProposal.objects.create(created_by=self.user_creator,
                                           poll_id=poll_id,
                                           title=title,
                                           description=description)

    def generate_voting_environment(self):
        poll = self.generate_poll()
        proposal = [self.generate_proposal(poll_id=poll.id, title=f'test_proposal_{n+1}')
                    for n in range(3)]
        return [poll, *proposal]


    def test_poll_create(self):
        poll = poll_create(user_id=self.user_creator.user.id, group_id=self.group.id,
                           title='test_poll', description='test_description',
                           start_date=datetime.now(tz=timezone.utc),
                           end_date=datetime.now(tz=timezone.utc) + timedelta(hours=2),
                           poll_type=1, tag=self.tag_one.id, dynamic=True)

        self.assertTrue(isinstance(poll, Poll))

    def test_poll_update(self):
        poll = self.generate_poll()

        self.assertEqual(poll_update(user_id=self.user_creator.user.id,
                                     group_id=self.group.id,
                                     poll_id=poll.id,
                                     data=dict(title='updated_test_poll')).title,
                         'updated_test_poll')

    def test_poll_delete(self):
        poll = self.generate_poll()

        deleted_id = poll.id
        poll_delete(user_id=self.user_creator.user.id, group_id=self.group.id, poll_id=deleted_id)

    def test_proposal_create(self):
        poll = self.generate_poll()
        proposal = poll_proposal_create(user_id=self.user_creator.user.id,
                                        group_id=self.group.id,
                                        poll_id=poll.id,
                                        title='test_proposal',
                                        description='test_description')

        self.assertTrue(isinstance(proposal, PollProposal))

    def test_proposal_delete(self):
        poll = self.generate_poll()
        proposal = self.generate_proposal(poll_id=poll.id)

        poll_proposal_delete(user_id=self.user_creator.user.id,
                             group_id=self.group.id,
                             proposal_id=proposal.id)

    def test_vote_update(self):
        poll, proposal_one, proposal_two, proposal_three = self.generate_voting_environment()
        poll_proposal_vote_update(user_id=self.user_creator.user.id,
                                  group_id=self.group.id,
                                  poll_id=poll.id,
                                  data=[proposal_one.id, proposal_two.id, proposal_three.id])

    def test_poll_finish(self):
        poll, proposal_one, proposal_two, proposal_three = self.generate_voting_environment()
        poll_proposal_vote_update(user_id=self.user_creator.user.id,
                                  group_id=self.group.id,
                                  poll_id=poll.id,
                                  data=[proposal_one.id, proposal_two.id, proposal_three.id])
        poll_finish(poll_id=poll.id)
        poll.refresh_from_db()
        self.assertTrue(poll.finished)

    def test_poll_refresh(self):
        poll, proposal_one, proposal_two, proposal_three = self.generate_voting_environment()
        poll_proposal_vote_update(user_id=self.user_creator.user.id,
                                  group_id=self.group.id,
                                  poll_id=poll.id,
                                  data=[proposal_one.id, proposal_two.id, proposal_three.id])
        poll_refresh_cheap(poll_id=poll.id)
        poll.refresh_from_db()
        self.assertEqual(poll.participants, 0)
