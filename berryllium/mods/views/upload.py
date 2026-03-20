from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.forms import formset_factory, inlineformset_factory, modelformset_factory

from berryllium.mods.forms import (
    FileUploadForm,
    MetadataForm,
    FileGroupForm,
    SingleFileForm,
)
from berryllium.mods.models import Mod, FileGroup, FileUpload
from berryllium.mods.services import init_context, upload_file
from berryllium.mods.settings import UPLOAD_NAVIGATION


def upload_mod(request):
    """
    Landing page for mod upload requests.
    # TODO: Clear session to start fresh.
    """
    return render(
        request,
        "mods/upload/base.html",
        {
            "form": FileUploadForm(),
            "mod_navigation": UPLOAD_NAVIGATION,
        },
    )


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
            # Rehydrate form with draft data
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
    file_url = ""

    # rehydrate file data (file url only if GET)
    if mod_id:
        mod = Mod.objects.get(id=mod_id)
        files = mod.files.all()
        file_url = mod.external_url if mod.is_external else ""

        if file_url:
            context["file_url"] = file_url

        if files.exists():
            existing_files = [f for f in files.values("filename", "size", "id")]
            context["existing_files"] = existing_files

    # ---------------------- POST (Handle file uploads and navigation)
    if request.method == "POST":
        # get existing uploaded files saved in draft

        # ----------------- Handle previous navigation
        # validation not needed for back navigation
        if request.POST.get("action") == "previous":
            return redirect("upload_step1")

        form = FileUploadForm(
            request.POST, request.FILES, existing_files=existing_files
        )

        if form.is_valid():
            clean_file = form.cleaned_data["file"]
            clean_url = form.cleaned_data["file_url"]

            if clean_file:
                file = upload_file(clean_file, mod_id=mod_id)
                if file:
                    # update existing_files for re-rendering form with new file
                    existing_files.append(file)
                    context["existing_files"] = existing_files

            # ------------------ Handle next navigation
            if request.POST.get("action") == "next":
                print("Next button clicked.")
                if clean_url:
                    mod = Mod.objects.filter(id=mod_id).first()
                    # TODO: Cleanup temp files and rework filegroups with url-based mods
                    if mod:
                        mod.is_external = True
                        mod.external_url = clean_url
                        mod.save()

                return redirect("upload_step3")

            # ----------------- Simple file upload without navigation (stay on step 2)
            else:
                return render(request, "mods/upload/step/2.html", context)

        # ---------------------- Invalid form: return SAME state with errors
        context["form"] = form
        return render(request, "mods/upload/step/2.html", context)

    # ---------------------- GET
    return render(request, "mods/upload/step/2.html", context)


def upload_step3(request):
    """
    Step 3 of upload form.
    """
    context = init_context(current_index=2, form=FileGroupForm())
    # TODO: iterative through formsets to validate forms
    FileGroupFormset = formset_factory(FileGroupForm, fields=["group_name", "group_description"], extra=0)
    SingleFileFormset = inlineformset_factory(FileGroup, FileUpload, fields=["title", "description"], extra=0)
    filegroupforms = FileGroupFormset(prefix="groups")
    singlefileforms = SingleFileFormset(prefix="files")

    mod_id = request.session.get("session_id")
    mod = Mod.objects.filter(id=mod_id).first()
    uploaded_files = mod.files.all() if mod else []
    context["uploaded_files"] = uploaded_files
    context["file_groups"] = [fg for fg in mod.file_groups.all()] if mod else []

    # ---------------- POST (Back/Next) uses formset validation
    if request.method == "POST":
        form = FileGroupForm(request.POST)

        # if form isn't valid, return same page with errors
        if not form.is_valid():
            return render(request, "mods/upload/step/3.html", context)
        action = request.POST.get("action")

        if action in ("next", "previous"):
            if action == "previous":
                return redirect("upload_step2")
            if action == "next":
                return redirect("upload_step4")

    # ---------------- GET (rehydrate Alpine)
    context["filegroupforms"] = filegroupforms
    context["singlefileforms"] = singlefileforms
    return render(request, "mods/upload/step/3.html", context)


def upload_step4(request):
    return render(
        request, "mods/upload/step/4.html", context=init_context(current_index=3)
    )


# TODO: Fix latency issues with HX requests (takes forever between initial upload and response)
@require_http_methods(["POST"])
def remove_temp_file(request, file_id):
    """
    Delete a file from current session.
    """
    mod_id = request.session.get("session_id")
    if request.method == "POST":
        mod = Mod.objects.filter(id=mod_id).first()
        temp_files = mod.files.all() if mod else []

        # find file by id in temp_files
        file = temp_files.filter(id=file_id).first()
        temp_path = []
        if file:
            file.delete()
            temp_path = file.staged_file.path

        # Delete from storage (in case row was missing)
        if temp_path and default_storage.exists(temp_path):
            default_storage.delete(temp_path)

        return HttpResponse("")


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
