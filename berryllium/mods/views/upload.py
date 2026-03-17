import os
import uuid

from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.forms import modelformset_factory
from django.views.decorators.http import require_http_methods

from ..forms import FileUploadForm, MetadataForm, FileGroupFormSet, FileDetailsForm
from ..models import FileUpload, Mod

# Navigation configuration for upload form
#     name: Current location title
#     url: Reference Django url
#     icon: Icon name. See: https://icons.getbootstrap.com/
NAVIGATION = [
    {"name": "Basic Information", "url": "upload_step1", "icon": "info-circle"},
    {"name": "Upload Files", "url": "upload_step2", "icon": "upload"},
    {"name": "Organize Files", "url": "upload_step3", "icon": "folder"},
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
        "nav_item_count": nav_item_count,
        "current_nav_index": 0,
        "progress_range": progress_range,
        "remainder_range": remainder_range,
    }

    if request.method == "POST":
        form = MetadataForm(request.POST)
        if form.is_valid():
            # Save data in db
            mod = form.save(commit=False)
            mod.save()

            # create a session id tied to the mod to make sure
            # every step saves to correct mod instance
            request.session["session_id"] = mod.id

            # Return NEXT state (step 2) on success
            return redirect("upload_step2")

        # Invalid: return SAME state with errors
        context["form"] = form
        return render(request, "mods/upload/step/1.html", context=context)
    
    elif request.method == "GET" and request.session.get("session_id"):
        # Send draft data if it exists
        mod_id = request.session["session_id"]
        try:
            mod = Mod.objects.get(id=mod_id)
            form = MetadataForm(instance=mod)
        except Mod.DoesNotExist:
            form = MetadataForm()
            
        form = MetadataForm()

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
                return redirect("upload_step3")
            elif request.POST.get("action") == "previous":
                return redirect("upload_step1")
            else:
                return render(request, "mods/upload/step/2.html", context)

        context["form"] = form  # return form with errors if invalid
        return render(request, "mods/upload/step/2.html", context)

    # GET
    return render(request, "mods/upload/step/2.html", context)


# TODO: Move validation and cleanup to form
def update_step3_state(request, uploaded_files, template_obj):
    """
    Updates step3 state and some validation.
    """
    group_formset = FileGroupFormSet(request.POST, prefix="groups")

    FileDetailsFormSet = modelformset_factory(FileUpload, form=FileDetailsForm, extra=0)
    file_formset = FileDetailsFormSet(
        request.POST, queryset=uploaded_files, prefix="files"
    )

    if group_formset.is_valid() and file_formset.is_valid():
        groups_data = []
        for form in group_formset:
            if form.cleaned_data and not form.cleaned_data.get("DELETE"):
                groups_data.append(
                    {
                        "name": form.cleaned_data["name"],
                        "description": form.cleaned_data.get("description", ""),
                        "order": form.cleaned_data.get("order", 0),
                    }
                )

        files_data = []
        # Structure data into json serializable format
        for form in file_formset:
            if form.cleaned_data:
                files_data.append(
                    {
                        "id": form.instance.id,
                        "title": form.cleaned_data.get("title", ""),
                        "description": form.cleaned_data.get("description", ""),
                        "group_index": form.cleaned_data["group_index"],
                        "file_order": form.cleaned_data["file_order"],
                    }
                )

        request.session["file_groups"] = groups_data
        request.session["file_details"] = files_data
        request.session.modified = True

        return group_formset, file_formset, uploaded_files

    # else return to step 3 with errors
    return render(
        request,
        template_obj,
        {
            "group_formset": group_formset,
            "file_formset": file_formset,
            "uploaded_files": uploaded_files,
        },
    )


def upload_step3(request):
    """
    Step 3 of upload form.
    """
    session_id = _get_upload_session_id(request)
    current_index = 3
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

    # TODO: rework to use context instead of passing uploaded_files separately

    uploaded_files = FileUpload.objects.filter(upload_session=session_id).order_by(
        "date", "id"
    )
    if not uploaded_files.exists():
        return render(
            request,
            "mods/upload/step/2.html",
            {
                "form": FileUploadForm(),
                "existing_files": request.session.get("temp_uploaded_files", []),
                "error": "Upload at least one file before organizing.",
            },
        )

    # ---------------- POST (Back/Next) uses formset validation
    if request.method == "POST":
        action = request.POST.get("action")

        if action in ("next", "previous"):
            res = update_step3_state(request, uploaded_files, "mods/upload/step/3.html")
            # if invalid, res will be None -> fall through and re-render with errors
            if res is not None:
                return res
            if action == "previous":
                return redirect("create_mods_step2")
            if action == "next":
                # IMPORTANT: go to step 4 (don’t re-render step3)
                return redirect("create_mods_step4")

    # ---------------- GET (rehydrate Alpine)
    groups_init = request.session.get("file_groups", [])
    if not groups_init:
        groups_init = [{"name": "Files", "description": "", "order": 0}]

    existing_file_details = request.session.get("file_details", [])
    by_id = {fd.get("id"): fd for fd in existing_file_details if fd.get("id")}

    files_init = []
    for i, uf in enumerate(uploaded_files):
        fd = by_id.get(uf.id, {})
        files_init.append(
            {
                "id": uf.id,
                "filename": uf.filename,
                "title": fd.get("title", ""),
                "description": fd.get("description", ""),
                "group_index": int(fd.get("group_index", 0)),
                "file_order": int(fd.get("file_order", i)),
            }
        )

    return render(
        request,
        "mods/upload/step/3.html",
        {
            "uploaded_files": uploaded_files,
            "groups_init": groups_init,
            "files_init": files_init,
        },
    )


# TODO: Fix latency issues with HX requests (takes forever between initial upload and response)
@require_http_methods(["POST"])
def remove_temp_file(request, file_index):
    """
    Delete a file from current session.
    """
    if request.method == "POST":
        temp_files = request.session.get("temp_uploaded_files", [])

        if 0 <= file_index < len(temp_files):
            file_info = temp_files[file_index]

            # Delete UploadedFile row if present
            # TODO: restore file ID functionality
            uploaded_file_id = file_info.get("uploaded_file_id")
            if uploaded_file_id:
                try:
                    uploaded_file = FileUpload.objects.get(id=uploaded_file_id)
                except FileUpload.DoesNotExist:
                    uploaded_file = None
                if uploaded_file:
                    uploaded_file.delete()

            # Delete from storage (in case row was missing)
            temp_path = file_info.get("temp_path")
            if temp_path and default_storage.exists(temp_path):
                default_storage.delete(temp_path)

            temp_files.pop(file_index)
            request.session["temp_uploaded_files"] = temp_files
            request.session.modified = True

        return redirect("upload_step2")
