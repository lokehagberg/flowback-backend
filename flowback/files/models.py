import os.path

from django.db import models
from django.utils import timezone

from flowback.common.models import BaseModel
from flowback.user.models import User


# Create your models here.
class FileCollection(BaseModel):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)


class FileSegment(BaseModel):
    collection = models.ForeignKey(FileCollection, on_delete=models.CASCADE)
    file = models.FileField()
    file_name = models.CharField(max_length=255)
