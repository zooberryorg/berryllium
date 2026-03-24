from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.generic import CreateView, TemplateView

from berryllium.mods.forms import (
    ModFileUploadForm,
    ModCategoriesForm,
    FileGroupForm,
)
from berryllium.mods.models import Mod, FileGroup
from berryllium.mods.services import (
    init_context,
    upload_file,
    create_file_group,
    create_filegroup_formsets,
)
from berryllium.mods.settings import UPLOAD_NAVIGATION


class ModCreateLanding(TemplateView):
    template_name = "mods/upload/base.html"
    success_url = "/mods/upload/s1"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mod_navigation"] = UPLOAD_NAVIGATION
        return context

    # def get(self, request, *args, **kwargs):
    #     # Clear session later to start new
    #     # request.session.pop("session_id", None)
    #     # request.session.pop("group_manager_toggled", None)
    #     return redirect("mod_create_step1")


def open_mod_draft(request, mod_id):
    """
    View to open an existing mod draft for editing.
    """
    try:
        mod = Mod.objects.get(id=mod_id, draft=True)
        request.session["session_id"] = (
            mod.id
        )  # Set session to load draft in upload steps
        return redirect("mod_create_step1")  # Redirect to step 1 to load draft data
    except Mod.DoesNotExist:
        print(f"Draft mod with ID {mod_id} does not exist.")
        # redirect to home
        return redirect("home")
    # TODO: Add error handling for non-existent or non-draft mods
    # except Mod.DoesNotExist:
    #     return render(request, "mods/explore/draft_not_found.html", {"mod_id": mod_id})


class ModCreateStep1(CreateView):
    model = Mod
    form_class = ModCategoriesForm
    template_name = "mods/upload/step/1.html"
    success_url = "/mods/upload/s2"

    def form_valid(self, form):
        """
        Validate form and save draft mod, then store mod ID in session for later steps.
        """
        response = super().form_valid(form)
        self.request.session["session_id"] = self.object.id
        return response

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form, including progress bar information.
        """
        context = super().get_context_data(**kwargs)
        progress_bar = init_context(current_index=0)
        return context | progress_bar

    def get_form_kwargs(self):
        """
        Re-hydrate form with existing draft data if session exists.
        """
        kwargs = super().get_form_kwargs()
        session_id = self.request.session.get("session_id")
        if session_id:
            try:
                kwargs["instance"] = Mod.objects.get(id=session_id)
            except Mod.DoesNotExist:
                pass
        return kwargs

def mod_create_step2(request):
    """
    Step 2 of the upload form.
    """
    context = init_context(current_index=1, form=ModFileUploadForm())
    mod_id = request.session.get("session_id")
    existing_files = []

    # rehydrate file data (file url only if GET)
    if mod_id:
        mod = Mod.objects.get(id=mod_id)
        files = mod.files.all()

        if files.exists():
            existing_files = [f for f in files.values("filename", "size", "id")]
            context["existing_files"] = existing_files

    # ---------------------- POST (Handle file uploads and navigation)
    if request.method == "POST":
        # get existing uploaded files saved in draft

        # ----------------- Handle previous navigation
        # validation not needed for back navigation
        if request.POST.get("action") == "previous":
            return redirect("mod_create_step1")

        form = ModFileUploadForm(
            request.POST, request.FILES, existing_files=existing_files
        )

        if form.is_valid():
            clean_file = form.cleaned_data["file"]

            if clean_file:
                file = upload_file(clean_file, mod_id=mod_id)
                if file:
                    # update existing_files for re-rendering form with new file
                    existing_files.append(file)
                    context["existing_files"] = existing_files

            # ------------------ Handle next navigation
            if request.POST.get("action") == "next":
                print("Next button clicked.")

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
    context["group_manager_toggled"] = request.session.get("group_manager_toggled")
    mod_id = request.session.get("session_id")

    file_group_forms, filegroups, group_formset = create_file_group(mod_id)

    # print the order of the files for debugging
    print("FileUpload order in view:")
    for group in filegroups:
        print(f"Group: {group.name} - order: {group.order}")
        for file in group.files.all():
            print(f"-------------- {file.filename} - order: {file.order}")
        print("\n")

    # ---------------- POST (Back/Next) uses formset validation
    if request.method == "POST":
        if request.POST.get("action") == "previous":
            return redirect("mod_create_step2")

        FileGroupFormset, SingleFileFormset = create_filegroup_formsets()
        # get formset data and validate
        group_formset = FileGroupFormset(request.POST, queryset=filegroups)
        if group_formset.is_valid():
            # only saves if data was changed
            saved_groups = group_formset.save()
            for group in saved_groups:
                # now that groups are saved, validate their files
                file_formset = SingleFileFormset(request.POST, instance=group)
                if file_formset.is_valid():
                    file_formset.save()
            # all valid, go to next step
            if request.POST.get("action") == "next":
                num_empty_groups = FileGroup.objects.filter(
                    mod_id=mod_id, files__isnull=True
                ).count()
                # first see if any empty file groups need to be deleted
                if num_empty_groups > 0:
                    # return form with modal asking user if they want to delete empty file group
                    context["file_groups"] = file_group_forms
                    context["num_empty_groups"] = num_empty_groups
                    return HttpResponse(status=400)
                return redirect("upload_step4")
        else:
            context["file_groups"] = file_group_forms
            context["group_formset"] = group_formset
            context["onEmptyGroupFound"] = False
            return render(request, "mods/upload/step/3.html", context)

    # ---------------- GET (rehydrate Alpine)
    context["file_groups"] = file_group_forms
    context["group_formset"] = group_formset
    context["onEmptyGroupFound"] = False
    return render(request, "mods/upload/step/3.html", context)


def upload_step4(request):

    return render(
        request,
        "mods/upload/step/4.html",
        context=init_context(current_index=3, form=None),
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
