from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.user.models import Report
from flowback.user.tests.factories import UserFactory, ReportFactory
from flowback.user.views.report import ReportCreateAPI


class UserTest(APITestCase):
    reset_sequences = True

    def setUp(self):
        self.users = [UserFactory() for x in range(3)]
        self.reports = [ReportFactory() for x in range(3)]

    def test_create_report(self):
        data = dict(title='hi', description='there')
        response = generate_request(api=ReportCreateAPI, data=data, user=self.users[0])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Report.objects.filter(user=self.users[0],
                                              title=data['title'],
                                              description=data['description']
                                              ).exists())

    def test_list_reports(self):
        self.assertEqual(Report.objects.count(), 3)
