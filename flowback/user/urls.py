from django.urls import path
from rest_framework.authtoken import views

from .views import (UserCreateApi,
                    UserCreateVerifyApi,
                    UserListApi,
                    UserGetApi,
                    UserUpdateApi,
                    UserForgotPasswordApi,
                    UserForgotPasswordVerifyApi)

user_patterns = [
    path('register/', UserCreateApi.as_view(), name='register'),
    path('register/verify/', UserCreateVerifyApi.as_view(), name='register_verify'),
    path('login/', views.obtain_auth_token, name='login'),
    path('forgot_password/', UserForgotPasswordApi.as_view(), name='forgot_password'),
    path('forgot_password/verify/', UserForgotPasswordVerifyApi.as_view(), name='forgot_password_verify'),
    path('users/', UserListApi.as_view(), name='users'),
    path('user/', UserGetApi.as_view(), name='user'),
    path('user/<int:user_id>/', UserGetApi.as_view(), name='user'),
    path('user/update/', UserUpdateApi.as_view(), name='user_update')
]
