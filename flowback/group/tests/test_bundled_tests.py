from django.test import TransactionTestCase

from rest_framework.validators import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.utils import IntegrityError

# Create your tests here.

from backend.settings import env

from flowback.group.selectors import group_user_permissions

from flowback.user.models import User

from flowback.group.models import (Group, GroupPermissions, GroupUser, GroupTags, GroupUserDelegator,
                                   GroupUserInvite)
from flowback.group.services import (group_create, group_update, group_delete, group_join,
                                     group_leave, group_invite, group_invite_accept, 
                                     group_invite_reject, group_invite_remove, group_user_delegate, 
                                     group_user_delegate_remove, group_user_delegate_update,
                                     group_permission_create, group_permission_delete,
                                     group_permission_update, group_tag_delete, group_tag_create, 
                                     group_user_update)


class CreateGroupTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.group_creation_env = env('FLOWBACK_ALLOW_GROUP_CREATION')
        self.user_creator = User.objects.create_superuser(username='creator_user',
                                                     email='creator@example.com',
                                                     password='password123')
        self.user_member = User.objects.create_user(username='member_user',
                                                    email='member@example.com',
                                                    password='password123')
        self.user_member_2 = User.objects.create_user(username='member_user_2',
                                                    email='member_2@example.com',
                                                    password='password123')
        self.group_open = group_create(user=self.user_creator.id, name='open_group', 
                                       description='test_description', image='test_img', 
                                       cover_image='test_cover_img', public=True,
                                       direct_join=True)
        self.group_indirect = group_create(user=self.user_creator.id, name='indirect_group', 
                                           description='test_description', image='test_img', 
                                           cover_image='test_cover_img', public=True,
                                           direct_join=False)
        self.group_closed = group_create(user=self.user_creator.id, name='closed_group', 
                                         description='test_description', image='test_img', 
                                         cover_image='test_cover_img', public=False,
                                         direct_join=False)
    
    def test_superuser_create_group(self):
        group_create(user=self.user_creator.id, name='super_created_group', 
                     description='test_description', image='test_img', 
                     cover_image='test_cover_img', public=False,
                     direct_join=False)

    def test_user_create_group(self):
        group_create(user=self.user_member.id, name='member_created_group', 
                     description='test_description', image='test_img', 
                     cover_image='test_cover_img', public=False,
                     direct_join=False)
    
    def test_create_already_existing_group(self):
        with self.assertRaises(DjangoValidationError):
            group_create(user=self.user_creator.id, name='open_group', 
                         description='second_test_description', image='second_test_img', 
                         cover_image='second_test_cover_img', public=False,
                         direct_join=False)

    # F.l.ow.b.a.c.k w.a.s c.r.e.a.t.e.d a.n.d p.r.o.j.e.c.t
    # l.e.a.d b.y L.o.k.e H.a.g.b.e.r.g.. T.h.e c.o.-.c.r.e.a.t.o.r.s o.f t.h.i.s v.e.r.s.i.o.n w.e.r.e.:
    # S.i.a.m.a.n.d S.h.a.h.k.a.r.a.m, E.m.i.l S.v.e.n.b.e.r.g a.n.d Y.u.l.i.y.a H.a.g.b.e.r.g..

    def test_creator_update_group(self):
        group_update(user=self.user_creator.id, group=self.group_open.id, 
                     data=dict(name='newer_test_group', 
                               description='new_description',
                               image='new_img',
                               cover_image='cover_img',
                               public=True,
                               direct_join=True))

    def test_non_member_update_group(self):
        with self.assertRaises(ValidationError):
            group_update(user=self.user_member.id, group=self.group_open.id,
                         data=dict(name='newest_test_group',
                                   description='newer_description',
                                   image='newer_img',
                                   cover_image='new_cover_img',
                                   public=True,
                                   direct_join=False))

    def test_update_group_to_identical_name(self):
        with self.assertRaises(DjangoValidationError):
            group_update(user=self.user_creator.id, group=self.group_open.id, 
                         data=dict(name='closed_group', 
                                   description='new_description',
                                   image='new_img',
                                   cover_image='cover_img',
                                   public=True,
                                   direct_join=True))

    def test_delete_group(self):
        group = group_create(user=self.user_creator.id, name='deletable_test_group', 
            description='test_description', image='test_img', 
            cover_image='test_cover_img', public=False,
            direct_join=False)
        group_delete(user=self.user_creator.id, group=group.id)
    
    def test_delete_already_deleted_group(self):
        with self.assertRaises(ValidationError):
            group_delete(user=self.user_creator.id, group=self.group_closed.id)
            group_delete(user=self.user_creator.id, group=self.group_closed.id)
    
    def test_non_member_join_group(self):
        group_join(user=self.user_member.id, group=self.group_open.id)

    def test_member_update_group(self):
        with self.assertRaises(ValidationError):
            group_join(user=self.user_member.id, group=self.group_open.id)
            group_update(user=self.user_member.id, group=self.group_open.id, 
                        data=dict(name='newest_test_group', 
                                description='newer_description',
                                image='newer_img',
                                cover_image='new_cover_img',
                                public=True,
                                direct_join=False))

    def test_super_join_group_already_joined(self):
        with self.assertRaises(ValidationError):
            group_join(user=self.user_creator.id, group=self.group_open.id)

    def test_member_join_group_already_joined(self):
        with self.assertRaises(ValidationError):
            group_join(user=self.user_member.id, group=self.group_open.id)
            group_join(user=self.user_member.id, group=self.group_open.id)
    
    def test_join_not_existing_group(self):
        with self.assertRaises(ValidationError):
            group_delete(user=self.user_creator.id, group=self.group_closed.id)
            group_join(user=self.user_member.id, group=self.group_closed.id)

    def test_leave_group(self): 
        group_leave(user=self.user_creator.id, group=self.group_open.id)

    def test_leave_group_already_left(self): 
        with self.assertRaises(ValidationError):
            group_leave(user=self.user_creator.id, group=self.group_open.id)
            group_leave(user=self.user_creator.id, group=self.group_open.id)

    def test_leave_group_not_joined(self): 
        with self.assertRaises(ValidationError):
            group_leave(user=self.user_member.id, group=self.group_open.id)

    def test_leave_not_existing_group(self): 
        with self.assertRaises(ValidationError):
            group_join(user=self.user_member.id, group=self.group_open.id)
            group_delete(user=self.user_creator.id, group=self.group_open.id)
            group_leave(user=self.user_member.id, group=self.group_open.id)

    def test_join_non_direct_join_group(self):
        with self.assertRaises(ValidationError):
            group_join(user=self.user_member.id, group=self.group_closed.id)

    def test_group_invite(self):
        group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)

    def test_group_invite_from_non_member(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_member.id, group=self.group_closed.id, to=self.user_member_2.id)

    def test_group_invite_to_self(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_creator.id)

    def test_group_invite_to_group_member(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
            group_invite_accept(user=self.user_member.id, group=self.group_closed.id)
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)

    def test_group_invite_to_already_invited(self):
        group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
        with self.assertRaises(DjangoValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)

    def test_group_invite_accept(self):
        group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
        group_invite_accept(user=self.user_member.id, group=self.group_closed.id)
    
    def test_group_invite_reject(self):
        group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
        group_invite_reject(user=self.user_member.id, group=self.group_closed.id)

    # def test_group_invite_remove(self):
    #     group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
    #     group_invite_reject(user=self.user_creator.id, group=self.group_closed.id)

    def test_group_invite_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group_delete(user=self.user_creator.id, group=self.group_closed.id)
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
    
    def test_group_invite_accept_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
            group_delete(user=self.user_creator.id, group=self.group_closed.id)
            group_invite_accept(user=self.user_member.id, group=self.group_closed.id)

    def test_group_invite_reject_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
            group_delete(user=self.user_creator.id, group=self.group_closed.id)
            group_invite_reject(user=self.user_member.id, group=self.group_closed.id)

    def test_group_invite_remove_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
            group_delete(user=self.user_creator.id, group=self.group_closed.id)
            group_invite_remove(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)

    def test_group_invite_accept_when_no_invite(self):
        with self.assertRaises(ValidationError):
            group_invite_accept(user=self.user_member.id, group=self.group_closed.id)

    def test_group_invite_reject_when_no_invite(self):
        with self.assertRaises(ValidationError):
            group_invite_reject(user=self.user_member.id, group=self.group_closed.id)
    
    def test_group_invite_remove_when_no_invite(self):
        with self.assertRaises(ValidationError):
            group_invite_remove(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)

    def test_group_invite_reject_after_accept(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
            group_invite_accept(user=self.user_member.id, group=self.group_closed.id)
            group_invite_reject(user=self.user_member.id, group=self.group_closed.id)

    def test_group_invite_remove_after_accept(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
            group_invite_accept(user=self.user_member.id, group=self.group_closed.id)
            group_invite_remove(user=self.user_creator.id, group=self.group_closed.id, to=self.user_member.id)
    
    # def test_group_invite_for_direct_join_group(self):
    #     with self.assertRaises(ValidationError):
    #         group_invite(user=self.user_creator.id, group=self.group_open.id, to=self.user_member.id)

    def test_update_group_user(self):
        group_join(user=self.user_member.id, group=self.group_open.id)
        user = group_user_update(user=self.user_member.id, group=self.group_open.id,
                                 fetched_by=self.user_creator.id, data=dict(delegate=True, is_admin=True))
        self.assertTrue(user.is_admin)
        self.assertTrue(not hasattr(user, 'groupuserdelegate'))

    def test_update_group_user_update(self):
        group_join(user=self.user_member.id, group=self.group_open.id)
        user = group_user_update(user=self.user_member.id, group=self.group_open.id,
                                 fetched_by=self.user_member.id, data=dict(delegate=True, is_admin=True))
        self.assertFalse(user.is_admin)
        self.assertTrue(hasattr(user, 'groupuserdelegate'))

    def test_update_group_user_update_by_non_authorized(self):
        group_join(user=self.user_member.id, group=self.group_open.id)
        group_join(user=self.user_member_2.id, group=self.group_open.id)
        user = group_user_update(user=self.user_member.id, group=self.group_open.id,
                                 fetched_by=self.user_member_2.id, data=dict(delegate=True, is_admin=True))
        self.assertFalse(user.is_admin)
        self.assertFalse(hasattr(user, 'groupuserdelegate'))

    def test_super_create_tag(self):
        group_tag_create(user=self.user_creator.id, group=self.group_open.id, tag_name="test")

    def test_super_create_tag_twice(self):
        with self.assertRaises(DjangoValidationError):
            group_tag_create(user=self.user_creator.id, group=self.group_open.id, tag_name="test")
            group_tag_create(user=self.user_creator.id, group=self.group_open.id, tag_name="test")

    def test_member_create_tag(self):
        with self.assertRaises(ValidationError):
            group_join(user=self.user_member.id, group=self.group_open.id)
            group_tag_create(user=self.user_member.id, group=self.group_open.id, tag_name="test")

    def test_super_delete_tag(self):
        tag = group_tag_create(user=self.user_creator.id, group=self.group_open.id, tag_name="test")
        group_tag_delete(user=self.user_creator.id, group=self.group_open.id, tag=tag.id)

    def test_super_delete_non_existing_tag(self):
        with self.assertRaises(ValidationError):
            group_tag_delete(user=self.user_creator.id, group=self.group_open.id, tag=0)

    def test_super_delete_tag_twice(self):
        with self.assertRaises(ValidationError):
            tag = group_tag_create(user=self.user_creator.id, group=self.group_open.id, tag_name="test")
            group_tag_delete(user=self.user_creator.id, group=self.group_open.id, tag=tag.id)
            group_tag_delete(user=self.user_creator.id, group=self.group_open.id, tag=tag.id)

    def test_member_delete_tag(self):
        with self.assertRaises(ValidationError):
            group_join(user=self.user_member.id, group=self.group_open.id)
            tag = group_tag_create(user=self.user_creator.id, group=self.group_open.id, tag_name="test")
            group_tag_delete(user=self.user_member.id, group=self.group_open.id, tag=tag.id)
