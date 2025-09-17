from django.test import TestCase

from rest_framework.validators import ValidationError
from django.core.validators import ValidationError as CoreValidationError

# Create your tests here.
from flowback.user.models import OnboardUser, User
from flowback.user.services import user_create, user_create_verify


class CreateUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.user_create(username='test_user',
                                             email='example@example.com',
                                             password='password123')

    def test_create_user(self):
        user_create(username='new_test_user', email='new_example@example.com')

    def test_create_already_existing_user(self):
        with self.assertRaises(ValidationError):
            user_create(username='test_user', email='new_example@example.com')
            user_create(username='new_test_user', email='example@example.com')

    def test_verify_user(self):
        verification_code = user_create(username='new_test_user',
                                        email='new_example@example.com')
        user_create_verify(verification_code=verification_code,
                           password='SomeHardPassword23')

    def test_verify_user_bad_password(self):
        verification_code = user_create(username='new_test_user',
                                        email='new_example@example.com')
        with self.assertRaises(CoreValidationError):
            user_create_verify(verification_code=verification_code,
                               password='esp')

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
