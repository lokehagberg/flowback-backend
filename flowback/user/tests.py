from django.test import TestCase

from rest_framework.validators import ValidationError
from django.core.validators import ValidationError as CoreValidationError

# Create your tests here.
from flowback.user.models import User
from flowback.user.services import (user_create, user_create_verify, user_update,
                                    user_forgot_password, user_forgot_password_verify)


class CreateUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user',
                                             email='example@example.com',
                                             password='password123')

        self.password_fail = 'esp'
        self.password_success = 'SomePassword510'

    def test_create_user(self):
        user_create(username='new_test_user', email='new_example@example.com')

    def test_create_already_existing_user(self):
        with self.assertRaises(ValidationError):
            user_create(username='test_user', email='new_example@example.com')
            user_create(username='new_test_user', email='example@example.com')

    def test_verify_user(self):
        verification_code = user_create(username='new_test_user',
                                        email='new_example@example.com')
        user = user_create_verify(verification_code=verification_code,
                                  password=self.password_success)

        self.assertTrue(user.check_password(self.password_success))

    def test_verify_user_bad_password(self):
        verification_code = user_create(username='new_test_user',
                                        email='new_example@example.com')
        with self.assertRaises(CoreValidationError):
            user_create_verify(verification_code=verification_code,
                               password='esp')

    def test_password_reset_user(self):
        verification_code = user_forgot_password(email="example@example.com")

        user = user_forgot_password_verify(verification_code=verification_code,
                                           password=self.password_success)

        self.assertTrue(user.check_password(self.password_success))

    def test_password_reset_bad_password(self):
        verification_code = user_forgot_password(email="example@example.com")

        with self.assertRaises(CoreValidationError):
            user_forgot_password_verify(verification_code=verification_code, password='esp')

    def test_verify_already_existing_user(self):
        verification_code = user_create(username='new_test_user',
                                        email='new_example@example.com')
        verification_code_2 = user_create(username='new_test_user',
                                          email='new_example@example.com')
        user_create_verify(verification_code=verification_code,
                           password='SomeHardPassword23')

        with self.assertRaises(ValidationError):
            user_create_verify(verification_code=verification_code_2,
                               password='SomeHardPassword23')

    def test_update_user(self):
        user = self.user
        data = dict(username='updated_user',
                    bio='some_description')
        user_update(user=user, data=data)
        self.assertEqual(user.username, 'updated_user')
        self.assertEqual(user.bio, 'some_description')
