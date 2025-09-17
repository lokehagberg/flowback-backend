from django.test import TestCase

from rest_framework.validators import ValidationError
from django.core.validators import ValidationError as CoreValidationError

# Create your tests here.

from flowback.group.selectors import group_user_permissions

from flowback.user.models import User

from flowback.group.models import (Group, GroupPermissions, GroupUser, GroupTags, GroupUserDelegate, 
                                   GroupUserInvite)
from flowback.group.services import (group_create, group_update, group_delete, group_join,
                                     group_leave, group_invite, group_invite_accept, 
                                     group_invite_reject, group_invite_remove, group_user_delegate, 
                                     group_user_delegate_remove, group_user_delegate_update)


class CreateGroupTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='test_user',
                                             email='example@example.com',
                                             password='password123')
        self.group = group_create(user=self.user.id, name='test_group', 
                                  description='test_description', image='test_img', 
                                  cover_image='test_cover_img', public=1, 
                                  direct_join=1)
    
    def test_create_group(self):
        group_create(user=self.user.id, name='new_test_group', 
                    description='test_description', image='test_img', 
                    cover_image='test_cover_img', public=0, 
                    direct_join=0)
    
    def test_create_already_existing_group(self):
        with self.assertRaises(ValidationError):
            group_create(user=self.user.id, name='test_group', 
                        description='new_test_description', image='new_test_img', 
                        cover_image='new_test_cover_img', public=0, 
                        direct_join=0)

    def test_update_group(self):
        group_update(user=self.user.id, group=self.group.id, data=dict(name='newer_test_group', 
                                                                       description='new_description',
                                                                       image='new_img',
                                                                       cover_image='cover_img',
                                                                       public=1,
                                                                       direct_join=1))
    
    def test_update_group_to_identical_name(self):
        with self.assertRaises(ValidationError):
            group_update(user=self.user.id, group=self.group.id, data=dict(name='newer_test_group', 
                                                                            description='new_description',
                                                                            image='new_img',
                                                                            cover_image='cover_img',
                                                                            public=1,
                                                                            direct_join=1))

    def test_delete_group(self):
        group = group_create(user=self.user.id, name='deletable_test_group', 
            description='test_description', image='test_img', 
            cover_image='test_cover_img', public=0, 
            direct_join=0)
        group_delete(user=self.user.id, group=group.id)
    
    def test_delete_already_deleted_group(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='deletable_test_group', 
                                 description='test_description', image='test_img', 
                                 cover_image='test_cover_img', public=0, 
                                 direct_join=0)
            group_delete(user=self.user.id, group=group.id)
            group_delete(user=self.user.id, group=group.id)
    
    def test_join_group(self):
        user = self.user = User.objects.create_user(username='tester_1',
                                        email='example1@example.com',
                                        password='password123')
        group_join(user=user, group=self.group.id)

    def test_join_group_already_joined(self):
        with self.assertRaises(ValidationError):
            group_join(user=self.user.id, group=self.group.id)
            group_join(user=self.user.id, group=self.group.id)

    def test_join_not_existing_group(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='deletable_test_group', 
                                 description='test_description', image='test_img', 
                                 cover_image='test_cover_img', public=1, 
                                 direct_join=1)
            group_delete(user=self.user.id, group=group.id)
            group_join(user=self.user.id, group=group.id)

    def test_leave_group(self): 
        group_leave(user=self.user.id, group=self.group.id)

    def test_leave_group_already_left(self): 
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='leavable_test_group', 
                        description='test_description', image='test_img', 
                        cover_image='test_cover_img', public=1, 
                        direct_join=1)
            group_leave(user=self.user.id, group=group.id)
            group_leave(user=self.user.id, group=group.id)
    
    def test_leave_not_existing_group(self): 
        with self.assertRaises(ValidationError):
            user = self.user = User.objects.create_user(username='tester_2',
                                                        email='example2@example.com',
                                                        password='password123')
            group = group_create(user=self.user.id, name='deletable_test_group', 
                                 description='test_description', image='test_img', 
                                 cover_image='test_cover_img', public=1, 
                                 direct_join=1)
            group_join(user=user.id, group=group.id)
            group_delete(user=self.user.id, group=group.id)
            group_leave(user=user.id, group=group.id)

    def test_join_non_direct_join_group(self):
        with self.assertRaises(ValidationError):
            user = self.user = User.objects.create_user(username='tester_3',
                                                        email='example3@example.com',
                                                        password='password123')
            group = group_create(user=self.user.id, name='private_test_group', 
                                 description='test_description', image='test_img', 
                                 cover_image='test_cover_img', public=1, 
                                 direct_join=0)
            group_join(user=user.id, group=group.id)

    def test_group_invite(self):
        group = group_create(user=self.user.id, name='secret_group_1', 
                        description='test_description', image='test_img', 
                        cover_image='test_cover_img', public=0, 
                        direct_join=0)
        user = self.user = User.objects.create_user(username='tester_4',
                                            email='example4@example.com',
                                            password='password123')
        group_invite(user=self.user.id, group=group.id, to=user.id)

    def test_group_invite_to_self(self):
        with self.assertRaises(ValidationError):
            group_invite(user=self.user.id, group=self.group.id, to=self.user.id)

    def test_group_invite_to_group_member(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secretest_group', 
                            description='test_description', image='test_img', 
                            cover_image='test_cover_img', public=0, 
                            direct_join=0)
            user = self.user = User.objects.create_user(username='tester_secreter',
                                                email='examplesecreter@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)
            group_invite_accept(user=user.id, group=group.id)
            group_invite(user=self.user.id, group=group.id, to=user.id)

    def test_group_invite_to_already_invited(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_2', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_5',
                                                email='example5@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)
            group_invite(user=self.user.id, group=group.id, to=user.id)

    def test_group_invite_accept(self):
        group = group_create(user=self.user.id, name='secret_group_3', 
                             description='test_description', image='test_img', 
                             cover_image='test_cover_img', public=0, 
                             direct_join=0)
        user = self.user = User.objects.create_user(username='tester_6',
                                            email='example6@example.com',
                                            password='password123')
        group_invite(user=self.user.id, group=group.id, to=user.id)
        group_invite_accept(user=user.id, group=group.id)
    
    def test_group_invite_reject(self):
        group = group_create(user=self.user.id, name='secret_group_4', 
                             description='test_description', image='test_img', 
                             cover_image='test_cover_img', public=0, 
                             direct_join=0)
        user = self.user = User.objects.create_user(username='tester_7',
                                            email='example7@example.com',
                                            password='password123')
        group_invite(user=self.user.id, group=group.id, to=user.id)
        group_invite_reject(user=user.id, group=group.id)

    def test_group_invite_remove(self):
        group = group_create(user=self.user.id, name='secret_group_5', 
                             description='test_description', image='test_img', 
                             cover_image='test_cover_img', public=0, 
                             direct_join=0)
        user = self.user = User.objects.create_user(username='tester_8',
                                            email='example8@example.com',
                                            password='password123')
        group_invite(user=self.user.id, group=group.id, to=user.id)
        group_invite_remove(self.user.id, group=group.id, user=user.id)

    def test_group_invite_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_6', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_7',
                                                email='example7@example.com',
                                                password='password123')
            group_delete(user=self.user.id, group=group.id)
            group_invite(user=self.user.id, group=group.id, to=user.id)
    
    def test_group_invite_accept_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_7', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_8',
                                                email='example8@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)
            group_delete(user=self.user.id, group=group.id)
            group_invite_accept(user=user.id, group=group.id)

    def test_group_invite_reject_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_8', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_9',
                                                email='example9@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)
            group_delete(user=self.user.id, group=group.id)
            group_invite_reject(user=user.id, group=group.id)

    def test_group_invite_remove_when_group_unexistent(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_8', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_9',
                                                email='example9@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)
            group_delete(user=self.user.id, group=group.id)
            group_invite_remove(user=self.user.id, group=group.id)

    def test_group_invite_accept_when_no_invite(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_10', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_11',
                                                email='example11@example.com',
                                                password='password123')
            group_invite_accept(user=user.id, group=group.id)

    def test_group_invite_reject_when_no_invite(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_11', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_12',
                                                email='example12@example.com',
                                                password='password123')
            group_invite_reject(user=user.id, group=group.id)
    
    def test_group_invite_remove_when_no_invite(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_12', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_13',
                                                email='example13@example.com',
                                                password='password123')
            group_invite_remove(user=self.user.id, group=group.id)

    def test_group_invite_remove_when_no_invite(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group_12', 
                                description='test_description', image='test_img', 
                                cover_image='test_cover_img', public=0, 
                                direct_join=0)
            user = self.user = User.objects.create_user(username='tester_13',
                                                email='example13@example.com',
                                                password='password123')
            group_invite_remove(user=self.user.id, group=group.id)

    def test_group_invite_reject_after_accept(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group13', 
                            description='test_description', image='test_img', 
                            cover_image='test_cover_img', public=0, 
                            direct_join=0)
            user = self.user = User.objects.create_user(username='tester_14',
                                                email='example14@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)
            group_invite_accept(user=user.id, group=group.id)
            group_invite_reject(user=user.id, group=group.id)

    def test_group_invite_remove_after_accept(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group14', 
                            description='test_description', image='test_img', 
                            cover_image='test_cover_img', public=0, 
                            direct_join=0)
            user = self.user = User.objects.create_user(username='tester_15',
                                                email='example15@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)
            group_invite_accept(user=user.id, group=group.id)
            group_invite_remove(user=self.user.id, group=group.id, to=user.id)
    
    def test_group_invite_for_direct_join_group(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group15', 
                            description='test_description', image='test_img', 
                            cover_image='test_cover_img', public=1, 
                            direct_join=1)
            user = self.user = User.objects.create_user(username='tester_16',
                                                email='example16@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)

    def test_group_invite_for_non_public_group(self):
        with self.assertRaises(ValidationError):
            group = group_create(user=self.user.id, name='secret_group16', 
                            description='test_description', image='test_img', 
                            cover_image='test_cover_img', public=0, 
                            direct_join=1)
            user = self.user = User.objects.create_user(username='tester_17',
                                                email='example17@example.com',
                                                password='password123')
            group_invite(user=self.user.id, group=group.id, to=user.id)

    
    #TODO we do permission things at the end, and delegation stuff