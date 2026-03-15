import os
import uuid

from django.shortcuts import render, redirect
from django.core.files.storage import default_storage

from ..forms import FileUploadForm, MetadataForm
from ..models import FileUpload

# Navigation configuration for upload form
#     name: Current location title
#     url: Reference Django url
#     icon: Icon name. See: https://icons.getbootstrap.com/
NAVIGATION = [
    {"name": "Basic Information", "url": "upload_step1", "icon": "info-circle"},
    {'name': 'Upload Files', 'url': 'upload_step2', 'icon': 'upload'},
    # {'name': 'Organize Files', 'url': 'create_mods_step3', 'icon': 'folder'},
    # {'name': 'Review & Submit', 'url': 'create_mods_step4', 'icon': 'check-circle'},
]


def _get_upload_session_id(request):
    """
    Ensure a session key exists (needed to tie UploadedFile rows to a user’s draft upload).
    """
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def upload_mod(request):
    """
    Landing page for mod upload requests.
    """
    return render(
        request,
        "mods/upload/base.html",
        {
            "form": FileUploadForm(),
            "mod_navigation": NAVIGATION,
        },
    )


def upload_step1(request):
    """
    Step 1 of the upload form.
    """
    current_index = 1
    progress_range = range(current_index)
    remainder_range = range(current_index, len(NAVIGATION))
    nav_item_count = len(NAVIGATION)
    context = {
        "form": MetadataForm(),
        "filename": request.session.get("upload_original_name"),
        "nav_item_count": nav_item_count,
        "current_nav_index": 0,
        "progress_range": progress_range,
        "remainder_range": remainder_range,
    }

    if request.method == "POST":
        form = MetadataForm(request.POST)
        if form.is_valid():
            # Store metadata in session
            request.session["upload_metadata"] = form.cleaned_data

            # Return NEXT state (step 2) on success
            return redirect("upload_step2")

        # Invalid: return SAME state with errors
        context["form"] = form
        return render(request, "mods/upload/step/1.html", context=context)
    elif request.method == "GET" and request.session.get("upload_metadata"):
        # Send existing files for review at form initialization TODO: simply send a boolean
        form = MetadataForm(initial=request.session["upload_metadata"])
        context["form"] = form
        return render(request, "mods/upload/step/1.html", context=context)

    # GET: show fresh form
    return render(request, "mods/upload/step/1.html", context=context)


def upload_step2(request):
    """
    Step 2 of the upload form.
    """
    session_id = _get_upload_session_id(request)
    current_index = 2
    progress_range = range(current_index)
    remainder_range = range(current_index, len(NAVIGATION))
    nav_item_count = len(NAVIGATION)
    context = {
        "form": FileUploadForm(),
        "filename": request.session.get("upload_original_name"),
        "nav_item_count": nav_item_count,
        "current_nav_index": current_index - 1,
        "progress_range": progress_range,
        "remainder_range": remainder_range,
        "existing_files": request.session.get("temp_uploaded_files", []),
    }

    if request.method == "POST":
        form = FileUploadForm(
            request.POST, request.FILES, existing_files=context["existing_files"]
        )

        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]

            if uploaded_file:
                # Save to storage (temp namespace by session)
                basename = os.path.basename(uploaded_file.name)
                temp_filename = (
                    f"temp_uploads/{session_id}/{uuid.uuid4().hex}_{basename}"
                )
                temp_path = default_storage.save(temp_filename, uploaded_file)

                # Create DB row so Step 3 can actually query files
                uf = FileUpload(
                    size=uploaded_file.size,
                    filename=basename,
                    upload_session=session_id,
                )
                uf.file.name = temp_path  # point FileField at saved path
                uf.save()

                # Store metadata in session for Step 2 preview list + removal
                file_info = {
                    "temp_path": temp_path,
                    "original_name": basename,
                    "size": uploaded_file.size,
                    "content_type": getattr(uploaded_file, "content_type", ""),
                }
                context["existing_files"].append(file_info)
                request.session["temp_uploaded_files"] = context["existing_files"]
                request.session.modified = True

            if request.POST.get("action") == "next":
                if not request.session.get("temp_uploaded_files"):
                    form.add_error(
                        "file", "Please upload at least one file before continuing."
                    )
                    context["form"] = form
                    context["existing_files"] = request.session.get(
                        "temp_uploaded_files", []
                    )
                    return render(request, "mods/upload/step/2.html", context)
                return redirect("create_mods_step3")
            elif request.POST.get("action") == "previous":
                print("Going back to step 1 from step 2")
                return redirect("upload_step1")
            else:
                return render(request, "mods/upload/step/2.html", context)

        context["form"] = form  # return form with errors if invalid
        return render(request, "mods/upload/step/2.html", context)

    # GET
    return render(request, "mods/upload/step/2.html", context)
