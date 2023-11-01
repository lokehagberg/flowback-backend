import factory.django
from flowback.common.tests import faker
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import FileCollection, FileSegment
from ...user.tests.factories import UserFactory


class FileCollectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileCollection

    created_by = factory.SubFactory(UserFactory)


class FileSegmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileSegment

    collection = factory.SubFactory(FileCollectionFactory)
    file = SimpleUploadedFile('something.txt',
                              f'Silver?'.encode())
