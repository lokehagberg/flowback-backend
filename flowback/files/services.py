from typing import Union

from django.core.files import File

from .models import FileCollection, FileSegment
from ..user.models import User


def upload_collection(*, user_id: int, file: Union[list[File], File], upload_to="", upload_to_include_timestamp=True):
    files = file if isinstance(file, list) else [file]

    collection = FileCollection(created_by_id=user_id)
    collection.full_clean()
    collection.save()

    for file in [FileSegment(collection=collection,
                             file=x,
                             directory=upload_to,
                             include_timestamp=upload_to_include_timestamp) for x in files]:
        file.full_clean()
        file.save()

    return collection
