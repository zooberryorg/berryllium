import os
import uuid
import hashlib

from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.forms import modelformset_factory
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse

from ..forms import FileUploadForm, MetadataForm, FileGroupFormSet, FileDetailsForm
from ..models import FileUpload, Mod, FileGroup

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

# ----------------------- Helper functions ----------------------

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


def init_context(current_index, form):
    """
    Initializes the multi-step form context with navigation information and progress.
    """

    nav_length = len(NAVIGATION)

    return {
        "form": form,
        "nav_item_count": nav_length,
        "current_nav_index": current_index,
        "progress_range": range(current_index + 1),
        "remainder_range": range(current_index + 1, nav_length),
    }

def calculate_file_hash(file):
    """
    Calculates a hash for the given file.
    """

    hasher = hashlib.md5()
    for chunk in file.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()

def upload_file(uploaded_file, mod_id=None):
    """
    Handles file upload and validation.
    """
    # Save to storage (temp namespace by session)
    basename = os.path.basename(uploaded_file.name)
    # TODO: Make sure this path is consistent with other temp paths and is cleaned up properly
    temp_filename = f"temp_uploads/{mod_id}/{uuid.uuid4().hex}_{basename}"
    temp_path = default_storage.save(temp_filename, uploaded_file)

    # if no existing files, create FileGroup to store file
    fg = FileGroup.objects.filter(mod_id=mod_id).first()
    if not fg:
        fg = FileGroup.objects.create(mod_id=mod_id, name="Files")

    # Create DB row so Step 3 can actually query files
    uf = FileUpload(
        size=uploaded_file.size,
        filename=basename,
        staged_file=temp_path,
        filegroup=fg,
    )
    uf.save()

    return {"filename": basename, "size": uploaded_file.size, "id": uf.id}

# ----------------------- Views ----------------------

def open_mod_draft(request, mod_id):
    """
    View to open an existing mod draft for editing.
    """
    try:
        mod = Mod.objects.get(id=mod_id, draft=True)
        request.session["session_id"] = (
            mod.id
        )  # Set session to load draft in upload steps
        return redirect("upload_step1")  # Redirect to step 1 to load draft data
    except Mod.DoesNotExist:
        print(f"Draft mod with ID {mod_id} does not exist.")
        # redirect to home
        return redirect("home")
    # TODO: Add error handling for non-existent or non-draft mods
    # except Mod.DoesNotExist:
    #     return render(request, "mods/explore/draft_not_found.html", {"mod_id": mod_id})


def upload_step1(request):
    """
    Step 1 of the upload form.
    """
    context = init_context(current_index=0, form=MetadataForm())
    session_exists = request.session.get("session_id") is not None

    # --------------------- POST
    if request.method == "POST":
        form = MetadataForm(request.POST)
        if form.is_valid():
            # Save data in db
            data = {
                "title": form.cleaned_data["title"],
                "category": ",".join(form.cleaned_data.get("category", [])),
                "summary": form.cleaned_data["summary"],
                "game": ",".join(form.cleaned_data.get("game", [])),
                "expansions": ",".join(form.cleaned_data.get("expansions", [])),
            }

            mod_id = session_exists

            # If session exists, update draft mod
            if mod_id:
                Mod.objects.filter(id=mod_id, draft=True).update(**data)

            # If no session, create new draft mod
            else:
                mod = Mod.objects.create(**data)
                request.session["session_id"] = mod.id

            # Return NEXT state (step 2) on success
            return redirect("upload_step2")

        # Invalid: return SAME state with errors
        context["form"] = form
        return render(request, "mods/upload/step/1.html", context=context)

    # --------------------- GET with existing session
    elif request.method == "GET" and session_exists:
        # Send draft data if it exists
        mod_id = request.session["session_id"]
        try:
            mod = Mod.objects.get(id=mod_id)
            form = MetadataForm(
                initial={
                    "title": mod.title,
                    "category": mod.category.split(",") if mod.category else [],
                    "summary": mod.summary,
                    "game": mod.game.split(",") if mod.game else [],
                    "expansions": mod.expansions.split(",") if mod.expansions else [],
                }
            )
        except Mod.DoesNotExist:
            form = MetadataForm()

        context["form"] = form
        return render(request, "mods/upload/step/1.html", context=context)

    # --------------------- GET without session (new upload)
    return render(request, "mods/upload/step/1.html", context=context)


def upload_step2(request):
    """
    Step 2 of the upload form.
    """
    context = init_context(current_index=1, form=FileUploadForm())
    mod_id = request.session.get("session_id")
    existing_files = []

    # ---------------------- POST (Handle file uploads and navigation)
    if request.method == "POST":
        # get existing uploaded files saved in draft
        if mod_id:
            mod = Mod.objects.get(id=mod_id)
            files = mod.files.all()
            if files.exists():
                existing_files = [f for f in files.values("filename", "size", "id")]

        form = FileUploadForm(
            request.POST, request.FILES, existing_files=existing_files
        )

        if form.is_valid():
            clean_file = form.cleaned_data["file"]

            if clean_file:
                file = upload_file(clean_file, mod_id=mod_id)

                # update existing_files for re-rendering form with new file
                existing_files.append(file)
                context["existing_files"] = existing_files

            # ------------------ Handle next navigation
            if request.POST.get("action") == "next":
                if not existing_files:
                    form.add_error(
                        "file", "Please upload at least one file before continuing."
                    )
                    context["form"] = form
                    context["existing_files"] = []
                    return render(request, "mods/upload/step/2.html", context)

                return redirect("upload_step3")

            # ----------------- Handle previous navigation
            elif request.POST.get("action") == "previous":
                return redirect("upload_step1")

            # ----------------- Simple file upload without navigation (stay on step 2)
            else:
                return render(request, "mods/upload/step/2.html", context)

        # ---------------------- Invalid form: return SAME state with errors
        context["form"] = form
        return render(request, "mods/upload/step/2.html", context)

    # ---------------------- GET
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


@require_http_methods(["POST"])
def cancel_mod_upload(request):
    """
    Cancel and delete the current mod upload session.
    Note: live version will only delete session data. Live version
    will keep draft and temp files until a cleanup task runs,
    the mod is processed into a full mod, or the user manually deletes the draft.
    """
    mod_id = request.session.get("session_id")
    if mod_id:
        # Get all files with this session
        mod = Mod.objects.filter(id=mod_id).first()
        if mod:
            files = mod.files.all()
            for f in files:
                # Delete file from storage
                if f.staged_file and default_storage.exists(f.staged_file.name):
                    default_storage.delete(f.staged_file.name)
            # Delete session directory if it exists
            session_dir = f"temp_uploads/{mod_id}/"
            if default_storage.exists(session_dir):
                default_storage.delete(session_dir)
            # Delete draft mod
            mod.delete()

        # Clear session data related to the upload
        request.session.pop("session_id", None)
        request.session.modified = True

    # force htmx to redirect instead of trying to re-render
    response = HttpResponse()
    response["HX-Redirect"] = redirect("home").url
    return response
