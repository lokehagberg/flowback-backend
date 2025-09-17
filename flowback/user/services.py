import uuid

from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth.password_validation import validate_password

from rest_framework.exceptions import ValidationError

from backend.settings import EMAIL_HOST_USER, FLOWBACK_URL
from flowback.common.services import model_update
from flowback.user.models import User, OnboardUser, PasswordReset


def user_create(*, username: str, email: str) -> str:
    users = User.objects.filter(Q(email=email) | Q(username=username))
    if users.exists():
        for user in users:
            if user.email == email:
                raise ValidationError('Email already exists.')

            else:
                raise ValidationError('Username already exists.')

    user = OnboardUser.objects.create(email=email, username=username)

    link = f'Use this code to create your account: {user.verification_code}'
    if FLOWBACK_URL:
        link = f'''Use this link to create your account: {FLOWBACK_URL}/create_account/
                   ?email={email}&verification_code={user.verification_code}'''

    send_mail('Flowback Verification Code', link, EMAIL_HOST_USER, [email])

    return user.verification_code


def user_create_verify(*, verification_code: str, password: str):
    onboard_user = get_object_or_404(OnboardUser, verification_code=verification_code)

    if User.objects.filter(email=onboard_user.email).exists():
        raise ValidationError('Email already registered')

    elif User.objects.filter(username=onboard_user.username).exists():
        raise ValidationError('Username already registered')

    elif onboard_user.is_verified:
        raise ValidationError('Verification code has already been used.')

    validate_password(password)

    model_update(instance=onboard_user,
                 fields=['is_verified'],
                 data=dict(is_verified=True))

    return User.objects.create_user(username=onboard_user.username,
                                    email=onboard_user.email,
                                    password=password)


def user_forgot_password(*, email: str):
    user = get_object_or_404(User, email=email)

    password_reset = PasswordReset.objects.create(user=user)

    link = f'Use this code to reset your account password: {password_reset.verification_code}'

    if FLOWBACK_URL:
        link = f'''Use this link to reset your account password: {FLOWBACK_URL}/forgot_password/
                       ?email={email}&verification_code={password_reset.verification_code}'''

    send_mail('Flowback Verification Code', link, EMAIL_HOST_USER, [email])

    return password_reset.verification_code


def user_forgot_password_verify(*, verification_code: str, password: str):
    password_reset = get_object_or_404(PasswordReset, verification_code=verification_code)

    if password_reset.is_verified:
        raise ValidationError('Verification code has already been used.')

    validate_password(password)
    user = password_reset.user
    user.set_password(password)
    user.save()

    model_update(instance=password_reset,
                 fields=['is_verified'],
                 data=dict(is_verified=True))

    return user


def user_update(*, user: User, data) -> User:
    non_side_effects_fields = ['username', 'profile_image', 'banner_image', 'bio', 'website']

    user, has_updated = model_update(instance=user,
                                     fields=non_side_effects_fields,
                                     data=data)

    return user