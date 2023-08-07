from datetime import timezone, datetime, timedelta

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from flowback.common.services import get_object
from flowback.group.models import GroupUser, GroupUserDelegatePool
from flowback.group.services import group_create, group_permission_create, group_update, group_join, group_tag_create, \
    group_user_delegate_pool_create, group_user_delegate
from flowback.poll.models import Poll, PollProposal
from flowback.poll.services.poll import poll_create
from flowback.poll.services.proposal import poll_proposal_create
from flowback.poll.services.vote import poll_proposal_vote_update, poll_proposal_delegate_vote_update
from flowback.poll.views import DelegatePollVoteListAPI
from flowback.user.models import User


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
                                  direct_join=True,
                                  hide_poll_users=True)

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

        self.poll = poll_create(user_id=self.user_creator.user.id, group_id=self.group.id,
                           title='test_poll', description='test_description',
                           start_date=datetime.now(tz=timezone.utc) + timedelta(hours=0),
                           proposal_end_date=datetime.now(tz=timezone.utc) + timedelta(hours=1),
                           vote_start_date=datetime.now(tz=timezone.utc) + timedelta(hours=2),
                           delegate_vote_end_date=datetime.now(tz=timezone.utc) + timedelta(hours=3),
                           end_date=datetime.now(tz=timezone.utc) + timedelta(hours=4),
                           poll_type=Poll.PollType.RANKING, tag=self.tag_one.id, public=True, dynamic=True, pinned=False)

        self.proposal = poll_proposal_create(user_id=self.user_creator.user.id,
                                             group_id=self.group.id,
                                             poll_id=self.poll.id,
                                             title='test_proposal',
                                             description='test_description')

        self.proposal_two = poll_proposal_create(user_id=self.user_creator.user.id,
                                                 group_id=self.group.id,
                                                 poll_id=self.poll.id,
                                                 title='test_proposal_three',
                                                 description='test_description')

        self.proposal_three = poll_proposal_create(user_id=self.user_creator.user.id,
                                                   group_id=self.group.id,
                                                   poll_id=self.poll.id,
                                                   title='test_proposal_three',
                                                   description='test_description')

        self.poll.start_date = datetime.now(tz=timezone.utc) + timedelta(minutes=-2)
        self.poll.proposal_end_date = datetime.now(tz=timezone.utc) + timedelta(minutes=-1)
        self.poll.vote_start_date = datetime.now(tz=timezone.utc)
        self.poll.save()

        poll_proposal_delegate_vote_update(user_id=self.user_delegate.user.id,
                                           poll_id=self.poll.id,
                                           data=dict(votes=[self.proposal.id, self.proposal_three.id, self.proposal_two.id]))

    def test_delegate_pool_votes(self):
        factory = APIRequestFactory()
        user = self.user_creator.user
        view = DelegatePollVoteListAPI.as_view()

        request = factory.get('/group/poll/pool/1/votes?poll_id=1')
        force_authenticate(request, user=user)
        response = view(request, delegate_pool_id=1)

        print(response.data)
        print(PollProposal.objects.all())
