import factory

from flowback.comment.tests.factories import CommentSectionFactory
from flowback.common.tests import fake

from flowback.group.models import (Group,
                                   GroupUser,
                                   GroupTags,
                                   GroupThread,
                                   GroupPermissions,
                                   GroupUserInvite,
                                   GroupUserDelegate,
                                   GroupUserDelegatePool,
                                   GroupUserDelegator, GroupThreadVote, WorkGroup, WorkGroupUser,
                                   WorkGroupUserJoinRequest)
from flowback.kanban.models import KanbanEntry
from flowback.user.tests.factories import UserFactory


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    created_by = factory.SubFactory(UserFactory)
    name = factory.LazyAttribute(lambda _: fake.unique.first_name().lower())
    description = factory.LazyAttribute(lambda _: fake.bs())


class GroupUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupUser

    user = factory.SubFactory(UserFactory)
    group = factory.SubFactory(GroupFactory, created_by=user)
    is_admin = factory.LazyAttribute(lambda o: o.group.created_by == o.user)


class WorkGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkGroup

    name = factory.LazyAttribute(lambda _: fake.unique.first_name())
    group = factory.SubFactory(GroupFactory)


class WorkGroupUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkGroupUser

    group_user = factory.SubFactory(GroupUserFactory)
    work_group = factory.SubFactory(WorkGroupFactory, group=factory.SelfAttribute('..group_user.group'))


class WorkGroupJoinRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkGroupUserJoinRequest

    group_user = factory.SubFactory(GroupUserFactory)
    work_group = factory.SubFactory(WorkGroupFactory, group=factory.SelfAttribute('..group_user.group'))


class GroupTagsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupTags

    name = factory.LazyAttribute(lambda _: fake.unique.first_name().lower())
    group = factory.SubFactory(GroupFactory)


class GroupThreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupThread

    created_by = factory.SubFactory(GroupUserFactory)
    title = factory.LazyAttribute(lambda _: fake.unique.sentence(nb_words=10).lower())
    comment_section = factory.SubFactory(CommentSectionFactory)


class GroupThreadVoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupThreadVote

    created_by = factory.SubFactory(GroupUserFactory)
    thread = factory.SubFactory(GroupThreadFactory, created_by=factory.SelfAttribute('..created_by'))
    vote = factory.LazyAttribute(lambda _: fake.boolean())


class GroupPermissionsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupPermissions

    role_name = factory.LazyAttribute(lambda _: fake.unique.first_name())
    author = factory.SubFactory(GroupFactory)


class GroupUserInviteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupUserInvite

    user = factory.SubFactory(UserFactory)
    group = factory.SubFactory(GroupFactory)
    external = False


class GroupUserDelegatePoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupUserDelegatePool

    group = factory.SubFactory(GroupFactory)


class GroupUserDelegateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupUserDelegate

    group = factory.SubFactory(GroupFactory)
    group_user = factory.SubFactory(GroupUserFactory, group=factory.SelfAttribute('..group'))
    pool = factory.SubFactory(GroupUserDelegatePoolFactory, group=factory.SelfAttribute('..group'))


class GroupUserDelegatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupUserDelegator

    delegator = factory.SubFactory(GroupUserFactory)
    delegate_pool = factory.SubFactory(GroupUserDelegatePoolFactory)
    group = factory.SubFactory(GroupFactory)
    tags = factory.SubFactory(GroupTagsFactory)
