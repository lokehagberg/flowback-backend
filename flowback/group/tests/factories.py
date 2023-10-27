import factory

from flowback.comment.tests.factories import CommentSectionFactory
from flowback.common.tests import faker

from flowback.group.models import (Group,
                                   GroupUser,
                                   GroupTags,
                                   GroupThread,
                                   GroupPermissions,
                                   GroupUserInvite,
                                   GroupUserDelegate,
                                   GroupUserDelegatePool,
                                   GroupUserDelegator)
from flowback.user.tests.factories import UserFactory


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    created_by = factory.SubFactory(UserFactory)
    name = factory.LazyAttribute(lambda _: faker.unique.first_name().lower())
    description = factory.LazyAttribute(lambda _: faker.bs())


class GroupUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupUser

    user = factory.SubFactory(UserFactory)
    group = factory.SubFactory(Group)


class GroupTagsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupTags

    name = factory.LazyAttribute(lambda _: faker.unique.first_name().lower())
    group = factory.SubFactory(GroupFactory)


class GroupThreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupThread

    created_by = factory.SubFactory(GroupUserFactory)
    title = factory.LazyAttribute(lambda _: faker.unique.sentence(nb_words=10).lower())
    comment_section = factory.SubFactory(CommentSectionFactory)


class GroupPermissionsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupPermissions

    role_name = factory.LazyAttribute(lambda _: faker.unique.first_name())
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
    group_user = factory.SubFactory(GroupUser)
    pool = factory.SubFactory(GroupUserDelegatePoolFactory)


class GroupUserDelegatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupUserDelegator

    delegator = factory.SubFactory(GroupUserFactory)
    delegate_pool = factory.SubFactory(GroupUserDelegatePoolFactory)
    group = factory.SubFactory(GroupFactory)
    tags = factory.SubFactory(GroupTagsFactory)
