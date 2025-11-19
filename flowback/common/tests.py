import inspect
from typing import Type

from faker import Faker
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from flowback.user.models import User

fake = Faker()


def generate_request(api: Type[APIView],
                     data: dict = None,
                     url_params: dict = None,
                     user: User = None):

    if url_params is None:
        url_params = dict()

    factory = APIRequestFactory()
    method = [i[0] for i in inspect.getmembers(api, predicate=inspect.isfunction)]
    view = api.as_view()

    if all(['get' in method, 'post' in method]):
        raise NotImplementedError('generate_request is unable to handle requests with both get/post methods.')

    if 'get' in method:
        request = factory.get('', data=data, format='json')
    elif 'post' in method:
        request = factory.post('', data=data, format='json')
    else:
        raise NotImplementedError('Missing handling for APIView method besides get/post.')

    if user:
        force_authenticate(request, user=user)

    return view(request, **url_params)
