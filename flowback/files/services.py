import ntpath
import os
import uuid
from typing import Union

from django.core.files import File

from .models import FileCollection, FileSegment
from ..user.models import User


def upload_collection(*, user_id: int, file: Union[list[File], File], upload_to="",
                      upload_to_uuid=True, upload_to_include_timestamp=True):
    files = file if isinstance(file, list) else [file]
    data = []

    collection = FileCollection(created_by_id=user_id)
    collection.full_clean()
    collection.save()

    for file in files:
        file_name = file.name
        directory = upload_to

        if upload_to_uuid:
            extension = ntpath.splitext(file_name)
            extension = extension[1 if len(extension) > 1 else 0]
            file.name = uuid.uuid4().hex + extension

        data.append(dict(file_name=file_name,
                         directory=directory,
                         file=file))


    for file in [FileSegment(collection=collection,
                             file=file['file'],
                             directory=file['directory'],
                             file_name=file['file_name'],
                             include_timestamp=upload_to_include_timestamp) for file in data]:
        file.full_clean()
        file.save()

    return collection
