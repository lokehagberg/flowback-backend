import ntpath
import uuid
from typing import Union

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
from django.utils import timezone

from .models import FileCollection, FileSegment
from ..user.models import User


def upload_file_manager(*, upload_to: str,
                        files: list[InMemoryUploadedFile],
                        collection: FileCollection,
                        upload_to_uuid=True,
                        upload_to_include_timestamp=True):
    data = []
    if upload_to != "" and not upload_to.endswith("/"):
        upload_to += "/"

    if upload_to_include_timestamp:
        upload_to += timezone.now().strftime("%Y/%m/%d/")

    for file in files:
        file_name = file.name

        # Generates an uuid instead of a user-defined file name
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


# A function to allow uploading a collection of files to a specified directory
def upload_collection(*, user_id: int, file: Union[list[InMemoryUploadedFile], InMemoryUploadedFile], upload_to="",
                      upload_to_uuid=True, upload_to_include_timestamp=True) -> FileCollection:
    files = file if isinstance(file, list) else [file]

    collection = FileCollection(created_by_id=user_id)
    collection.full_clean()
    collection.save()

    upload_file_manager(upload_to=upload_to,
                        files=files,
                        collection=collection,
                        upload_to_uuid=upload_to_uuid,
                        upload_to_include_timestamp=upload_to_include_timestamp)

    return collection


def update_collection(*, user_id: int = None,
                      file_collection_id: int,
                      attachments_remove: list[int] = None,
                      attachments_add: list[InMemoryUploadedFile] | InMemoryUploadedFile = None,
                      upload_to="",
                      upload_to_uuid=True,
                      upload_to_include_timestamp=True):
    user = User.objects.get(id=user_id) if user_id else None

    if not (attachments_add or attachments_remove):
        return

    file_collection = FileCollection.objects.get(id=file_collection_id)

    if user:
        if file_collection.created_by_id != user_id and user.is_staff and attachments_add:
            raise ValidationError("Staff can only remove attachments.")

        elif not user.is_staff and file_collection.created_by_id != user_id:
            raise ValidationError("Only the author of the attachment can update it.")

    if (file_collection.filesegment_set.count() + (len(attachments_add or [])) - (len(attachments_remove or []))) > 10:
        raise ValidationError("Cannot add more than 10 attachments.")

    if attachments_remove:
        file_collection.filesegment_set.filter(id__in=attachments_remove).delete()

    if attachments_add:
        upload_file_manager(upload_to=upload_to,
                            files=attachments_add,
                            collection=file_collection,
                            upload_to_uuid=upload_to_uuid,
                            upload_to_include_timestamp=upload_to_include_timestamp)
