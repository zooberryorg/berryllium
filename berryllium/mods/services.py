import os
import uuid

from berryllium.mods.settings import NAVIGATION
from berryllium.mods.utils import calculate_file_hash
from berryllium.mods.models import FileGroup, FileUpload

from django.core.files.storage import default_storage


def init_context(current_index, form):
    """
    Initializes the multi-step form context with navigation information and progress.
    """
    context = {
        "form": form,
    }
    progress_bar = generate_progress_bar(current_index, total_steps=len(NAVIGATION))

    return context | progress_bar


def generate_progress_bar(current_index, total_steps):
    """
    Generates progress bar data for the upload steps.
    """

    title = f"Step {current_index + 1} of {total_steps}: {NAVIGATION[current_index]['name']}"

    completed_range = list(range(current_index + 1))
    remaining_range = list(range(current_index + 1, total_steps))

    return {
        "title": title,
        "completed": completed_range,
        "remaining": remaining_range,
        "total_steps": total_steps,
        "current_index": current_index,
    }


def upload_file(uploaded_file, mod_id=None):
    """
    Handles file upload and validation.
    """
    if mod_id is None:
        return None

    # Save to storage (temp namespace by session)
    basename = os.path.basename(uploaded_file.name)

    # TODO: Make sure this path is consistent with other temp paths and is cleaned up properly
    temp_filename = f"temp_uploads/{mod_id}/{uuid.uuid4().hex}_{basename}"

    # note: calc hash first because default_storage will end up
    # moving binary pointer to the end of the file which will
    # result in stale hash if we try to calculate after saving to storage
    # alternatively, reset pointer with uploaded_file.seek(0) to reset
    file_hash = calculate_file_hash(uploaded_file)

    # see if hash already exists in mod files
    existing_file = FileUpload.objects.filter(
        file_hash=file_hash, filegroup__mod_id=mod_id
    ).first()

    # if file duplicate, delete newly uploaded file from storage
    if existing_file:
        return None

    # find file group that this file belongs to (if it exists)
    fg, _ = FileGroup.objects.get_or_create(mod_id=mod_id, defaults={"name": "Files"})

    # once all clear, save file to storage
    temp_path = default_storage.save(temp_filename, uploaded_file)

    # Create DB row so Step 3 can actually query files
    uf = FileUpload.objects.create(
        size=uploaded_file.size,
        filename=basename,
        staged_file=temp_path,
        filegroup=fg,
        file_hash=file_hash,
    )

    return {"filename": basename, "size": uploaded_file.size, "id": uf.id}
