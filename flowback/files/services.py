import ntpath
import uuid
from typing import Union

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
from django.utils import timezone

from .models import FileCollection, FileSegment


# A function to allow uploading a collection of files to a specified directory
def upload_collection(*, user_id: int, file: Union[list[InMemoryUploadedFile], InMemoryUploadedFile], upload_to="",
                      upload_to_uuid=True, upload_to_include_timestamp=True) -> FileCollection:
    files = file if isinstance(file, list) else [file]
    data = []

    collection = FileCollection(created_by_id=user_id)
    collection.full_clean()
    collection.save()

    if upload_to != "" and not upload_to.endswith("/"):
        upload_to += "/"

    if upload_to_include_timestamp:
        upload_to += timezone.now().strftime("%Y/%m/%d/")

    for file in files:
        file_name = file.name

        # Generates an uuid instead of user defined file name
        if upload_to_uuid:
            extension = ntpath.splitext(file_name)
            extension = extension[1 if len(extension) > 1 else 0]
            file.name = uuid.uuid4().hex + extension

        default_storage.save(upload_to + file.name, ContentFile(file.read()))
        data.append(dict(file_name=file_name,
                         file=upload_to + file.name))

    for file in [FileSegment(collection=collection,
                             file=file['file'],
                             file_name=file['file_name']) for file in data]:
        file.full_clean()
        file.save()

    return collection
