import os
import uuid

from berryllium.mods.settings import UPLOAD_NAVIGATION
from berryllium.mods.utils import calculate_file_hash
from berryllium.mods.models import ModFileGroup, ModFile, ModImage
from berryllium.mods.forms import ModFileGroupForm

from django.core.files.storage import default_storage
from django.forms import modelformset_factory, inlineformset_factory


def init_context(current_index, form=None):
    """
    Initializes the multi-step form context with navigation information and progress.
    """
    progress_bar = generate_progress_bar(
        current_index, total_steps=len(UPLOAD_NAVIGATION)
    )

    if form:
        progress_bar["form"] = form

    return progress_bar


def generate_progress_bar(current_index, total_steps):
    """
    Generates progress bar data for the upload steps.
    """

    title = f"Step {current_index + 1} of {total_steps}: {UPLOAD_NAVIGATION[current_index]['name']}"

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
        print("No mod ID provided for file upload.")
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
    existing_file = ModFile.objects.filter(
        file_hash=file_hash, filegroup__mod_id=mod_id
    ).first()

    # if file duplicate, delete newly uploaded file from storage
    if existing_file:
        print("Duplicate file detected. Will not upload.")
        return None

    # find file group that this file belongs to (if it exists)
    fg = ModFileGroup.objects.filter(mod_id=mod_id).first()
    if fg is None:
        fg = ModFileGroup.objects.create(mod_id=mod_id, name="Files")

    # once all clear, save file to storage
    temp_path = default_storage.save(temp_filename, uploaded_file)

    # Create DB row so Step 3 can actually query files
    uf = ModFile.objects.create(
        size=uploaded_file.size,
        filename=basename,
        staged_file=temp_path,
        filegroup=fg,
        file_hash=file_hash,
        order=fg.files.count(),
    )

    return {"filename": basename, "size": uploaded_file.size, "id": uf.id}

def upload_image(uploaded_image, mod_id=None):
    """
    Handles image upload and validation.
    """
    if mod_id is None:
        print("No mod ID provided for image upload.")
        return None

    # Save to storage (temp namespace by session)
    basename = os.path.basename(uploaded_image.name)

    temp_filename = f"temp_uploads/{mod_id}/{uuid.uuid4().hex}_{basename}"

    # Save image to storage
    temp_path = default_storage.save(temp_filename, uploaded_image)
    print(f"Image saved to temporary path: {temp_path}")

    # create db row for img
    img = ModImage.objects.create(
        mod_id=mod_id,
        image=temp_path,
        title=basename,
        uploaded_by="temp_user",  # TODO: replace with user auth FK
        order=ModImage.objects.filter(mod_id=mod_id).count(),
    )

    return {"name": basename, "size": uploaded_image.size, "temp_path": temp_path, "id": img.id}


def create_filegroup_formsets(extra=0):
    return (
        modelformset_factory(ModFileGroup, form=ModFileGroupForm, extra=extra),
        inlineformset_factory(
            ModFileGroup, ModFile, fields=["title", "description"], extra=extra
        ),
    )


def create_file_group(mod_id):
    ModFileGroupFormset, ModFileFormset = create_filegroup_formsets()

    filegroups = ModFileGroup.objects.filter(mod_id=mod_id)
    group_formset = ModFileGroupFormset(queryset=filegroups)

    # pair each file group with its set of files
    return [
        [
            (filegroup_form, ModFileFormset(instance=filegroup_form.instance))
            for filegroup_form in group_formset.forms
        ],
        filegroups,
        group_formset,
    ]


def update_filegroup_order(mod_id):
    """
    Updates the order of file groups.
    """
    groups = ModFileGroup.objects.filter(mod_id=mod_id)
    if not groups:
        return False

    # update order
    for index, fg in enumerate(groups):
        fg.order = index
        fg.save()
    return True


def update_file_order(group, moved_file=None, index=None):
    files = list(ModFile.objects.filter(filegroup=group).order_by("order"))
    if not files:
        return
    if moved_file and index is not None:
        files.remove(moved_file)
        files.insert(index, moved_file)
    for i, f in enumerate(files):
        f.order = i
        f.save()


def swap_order(models, current_index, direction):
    """
    Swaps the order of file groups or files based on the direction.
    """
    if direction == "up" and current_index > 0:
        # swap with previous group
        models[current_index - 1], models[current_index] = (
            models[current_index],
            models[current_index - 1],
        )
    elif direction == "down" and current_index < len(models) - 1:
        # swap with next group
        models[current_index + 1], models[current_index] = (
            models[current_index],
            models[current_index + 1],
        )

    # save new order to database
    for index, fg in enumerate(models):
        fg.order = index
        fg.save()
