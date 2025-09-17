from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.server.views import ServerConfigListAPI


# Create your tests here.
class ServerTest(APITestCase):
    def test_get_public_config(self):
        response = generate_request(api=ServerConfigListAPI)
        print(response.data)