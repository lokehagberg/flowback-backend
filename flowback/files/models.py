import os.path

from django.db import models
from django.utils import timezone

from flowback.common.models import BaseModel
from flowback.common.validators import FieldNotBlankValidator


# Collection of files
class FileCollection(BaseModel):
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE)


# The files themselves
class FileSegment(BaseModel):
    collection = models.ForeignKey(FileCollection, on_delete=models.CASCADE)
    file = models.FileField()
    file_name = models.CharField(max_length=255, validators=[FieldNotBlankValidator])
