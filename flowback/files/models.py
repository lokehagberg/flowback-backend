import os.path

from django.db import models
from django.utils import timezone

from flowback.common.models import BaseModel
from flowback.user.models import User


# Create your models here.
class FileCollection(BaseModel):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)


class FileSegment(BaseModel):
    def __init__(self, directory="", include_timestamp=True, *args, **kwargs):
        self.directory = directory
        self.include_timestamp = include_timestamp

        super(FileSegment, self).__init__(*args, **kwargs)

    def upload_directory(self, file_name):
        directory = self.directory

        if self.directory != "" and not self.directory.endswith("/"):
            directory += "/"

        if self.include_timestamp:
            directory += timezone.now().strftime("%Y/%m/%d/")

        return directory + file_name

    collection = models.ForeignKey(FileCollection, on_delete=models.CASCADE)
    file = models.FileField(upload_to=upload_directory)
    file_name = models.CharField(max_length=255)
