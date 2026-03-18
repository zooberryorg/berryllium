

from berryllium.mods.settings import NAVIGATION


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
    }

def upload_file(uploaded_file, mod_id=None):
    """
    Handles file upload and validation.
    """
    # Save to storage (temp namespace by session)
    basename = os.path.basename(uploaded_file.name)
    # TODO: Make sure this path is consistent with other temp paths and is cleaned up properly
    temp_filename = f"temp_uploads/{mod_id}/{uuid.uuid4().hex}_{basename}"
    temp_path = default_storage.save(temp_filename, uploaded_file)
    file_hash = calculate_file_hash(uploaded_file)

    # if no existing files, create FileGroup to store file
    fg = FileGroup.objects.filter(mod_id=mod_id).first()

    # see if hash already exists in mod files
    existing_file = FileUpload.objects.filter(
        file_hash=file_hash, filegroup__mod_id=mod_id
    ).first()

    # if file exists, delete newly uploaded file from storage
    if existing_file:
        if default_storage.exists(temp_path):
            default_storage.delete(temp_path)
        return {}
    elif not fg:
        fg = FileGroup.objects.create(mod_id=mod_id, name="Files")

    # Create DB row so Step 3 can actually query files
    uf = FileUpload(
        size=uploaded_file.size,
        filename=basename,
        staged_file=temp_path,
        filegroup=fg,
        file_hash=file_hash,
    )
    uf.save()

    return {"filename": basename, "size": uploaded_file.size, "id": uf.id}

