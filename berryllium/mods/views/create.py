from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, Http404
from django.views.generic import CreateView, TemplateView, FormView, UpdateView
from django.urls import reverse, reverse_lazy as lazy_reverse
from django.shortcuts import get_object_or_404
from django.views import View
from urllib.parse import urlparse
from django.contrib.auth.mixins import LoginRequiredMixin

from berryllium.mods.forms import (
    ModFileUploadForm,
    ModCategorizationForm,
    ModImageUploadForm,
    ModDescriptionForm,
    ModGeneralInfoForm,
)
from berryllium.mods.models import Mod, ModImage
from berryllium.mods.services import (
    init_context,
    upload_file,
    create_file_group,
    create_filegroup_formsets,
    upload_image,
    image_gallery_context,
)
from berryllium.mods.settings import UPLOAD_NAVIGATION

class DraftModMixin:
    """Loads the mod from the URL's mod_id and checks this session created it."""

    def get_mod(self):
        if not hasattr(self, "_mod"):
            mod_id = self.kwargs["mod_id"]
            if mod_id not in self.request.session.get("draft_ids", []):
                raise Http404("Draft not found.")
            self._mod = get_object_or_404(Mod, id=mod_id)
        return self._mod

    def get_object(self, queryset=None):
        return self.get_mod()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mod"] = self.get_mod()
        context["mod_id"] = self.kwargs["mod_id"]
        return context

class UploadStepMixin(DraftModMixin):
    previous_step = None 

    def post(self, request, *args, **kwargs):
        if request.POST.get("action") == "previous" and self.previous_step:
            return redirect(self.previous_step, mod_id=self.kwargs["mod_id"])
        return super().post(request, *args, **kwargs)
    
    def render_to_response(self, context, **response_kwargs):
        is_htmx = self.request.headers.get("HX-Request")
        is_history_restore = self.request.headers.get("HX-History-Restore-Request")

        # if htmx request then update url in browser hist to current step
        if is_htmx and not is_history_restore:
            response = super().render_to_response(context, **response_kwargs)
            current_path = urlparse(self.request.headers.get("HX-Current-URL", "")).path
            if current_path != self.request.path:
                response["HX-Push-Url"] = self.request.path
            return response

        # if normal refresh then render base template with current step as initial step
        return render(self.request, "mods/create/base.html", {
            "mod_id": self.kwargs["mod_id"],
            "mod_navigation": UPLOAD_NAVIGATION,
            "initial_step_url": self.request.path,
        })

class ModDraftView(LoginRequiredMixin, CreateView):
    """
    HTMX Endpoint: Create a draft mod and return its ID for session management.
    """

    model = Mod
    form_class = ModGeneralInfoForm
    template_name = "mods/create/draft.html"

    def get_success_url(self):
        """
        Override to prevent redirect since we handle navigation with HTMX.
        """
        return reverse("mod_create_general", kwargs={"mod_id": self.object.id})

    def form_valid(self, form):
        """
        Create a new draft mod and return its ID in the response for session management.
        """
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        draft_ids = self.request.session.get("draft_ids", [])
        draft_ids.append(self.object.id)
        self.request.session["draft_ids"] = draft_ids
        self.request.session["session_id"] = self.object.id
        response = HttpResponse()
        response["HX-Redirect"] = self.get_success_url()
        return response

class ModCreateLanding(DraftModMixin, TemplateView):
    """
    Mod Creation Landing Page: Serves as base template for multi-step mod creation process.
    """

    template_name = "mods/create/base.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mod_navigation"] = UPLOAD_NAVIGATION
        context["initial_step_url"] = reverse("mod_create_general", kwargs={"mod_id": self.kwargs["mod_id"]})
        return context

    def get_success_url(self):
        """
        Override to prevent redirect since we handle navigation with HTMX.
        """
        return reverse("mod_create_general", kwargs={"mod_id": self.kwargs["mod_id"]})

    def get(self, request, *args, **kwargs):
        self.get_mod() # if draft doesnt exist or not in session, ret 404
        return redirect("mod_create_general", mod_id=self.kwargs["mod_id"])
    
class ModCreateGeneralInfo(UploadStepMixin, UpdateView):
    """
    Mod Creation Multi-Step 0: General Information (Title, Summary, etc.)
    """

    model = Mod
    form_class = ModGeneralInfoForm
    template_name = "mods/create/general/base.html"

    def get_success_url(self):
        """
        Override to prevent redirect since we handle navigation with HTMX.
        """
        return reverse("mod_create_categorization", kwargs={"mod_id": self.object.id})
    
    def form_valid(self, form):
        """
        Validate form and save draft mod, then store mod ID in session for later steps.
        """
        response = super().form_valid(form)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        progress_bar = init_context(current_index=0)
        return context | progress_bar
    
class ModCreateCategorization(UploadStepMixin, UpdateView):
    """
    Mod Creation Multi-Step 1: Select Categories and Create Draft Mod
    """

    model = Mod
    form_class = ModCategorizationForm
    template_name = "mods/create/categorization/base.html"
    previous_step = "mod_create_general"

    def form_valid(self, form):
        """
        Validate form and save draft mod, then store mod ID in session for later steps.
        """
        response = super().form_valid(form)
        return response
    
    def get_success_url(self):
        return reverse("mod_create_files", kwargs={"mod_id": self.object.id})

    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form, including progress bar information.
        """
        context = super().get_context_data(**kwargs)
        progress_bar = init_context(current_index=1)
        return context | progress_bar

class ModCreateFiles(UploadStepMixin, FormView):
    """
    Mod Creation Multi-Step 2: Upload Files and Organize into File Groups
    """

    form_class = ModFileUploadForm
    template_name = "mods/create/filemanager/base.html"
    previous_step = "mod_create_categorization"

    def get_success_url(self):
        if self.request.POST.get("action") == "uploaded_file":
            return self.request.path
        return reverse("mod_create_images", kwargs={"mod_id": self.kwargs["mod_id"]})
    
    def get_context_data(self, **kwargs):
        """
        Get context data for rendering the form, including existing uploaded files and progress bar information.
        """
        context = super().get_context_data(**kwargs)
        progress_bar = init_context(current_index=2)

        mod = self.get_mod()
        mod_id = mod.id
        existing_files = []
        existing_filegroups = []

        if mod_id:
            files = mod.files.all()

            # make formsets for existing file groups to render in template
            file_group_forms, filegroups, group_formset = create_file_group(mod_id)
            ModFileGroupFormset, ModFileFormset = create_filegroup_formsets()
            group_formset = ModFileGroupFormset(queryset=filegroups)

            if files.exists():
                existing_files = [f for f in files.values("filename", "size", "id")]
                context["existing_files"] = existing_files
            if filegroups.exists():
                existing_filegroups = filegroups.values("name", "id")
                print("Existing file groups:", existing_filegroups)
                context["file_groups"] = file_group_forms
                context["group_formset"] = group_formset

        return context | progress_bar

    def form_valid(self, form):
        """
        Handle file upload, save to storage, and re-render form with updated file list.
        """
        clean_file = form.cleaned_data["file"]
        mod_id = self.get_mod().id
        print(
            "form_valid called with file:",
            clean_file and clean_file.name,
            "and mod_id:",
            mod_id,
        )
        if clean_file:
            print("Attempting to upload file:", clean_file.name)
            file = upload_file(clean_file, mod_id=mod_id)
            if file:
                print("File uploaded successfully:", file)
                # re-render form with new file included in existing_files
                existing_files = self.get_context_data().get("existing_files", [])
                context = self.get_context_data()
                context["existing_files"] = existing_files
                return render(self.request, self.template_name, context)
            else:
                form.add_error("file", f'"{clean_file.name}" has already been uploaded to this mod.')
                return self.form_invalid(form)
        else:
            print("No file uploaded or file failed validation.")

        return super().form_valid(form)

class ModCreateImages(UploadStepMixin, FormView):
    """
    Mod Creation Multi-Step 3: Upload Pictures for the Mod
    """

    previous_step = "mod_create_files"

    form_class = (
        ModImageUploadForm  # Placeholder, replace with actual picture upload form
    )
    template_name = "mods/create/pictures/base.html"

    def get_success_url(self):
        return reverse("mod_create_description", kwargs={"mod_id": self.kwargs["mod_id"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        progress_bar = init_context(current_index=3)
        return context | progress_bar | image_gallery_context(self.get_mod().id)
    
    def form_valid(self, form):
        """
        Upload: save the images and re-render this step.
        Next (no images in the POST): continue to the description step.
        """
        uploaded_images = form.cleaned_data.get("image")
        if not uploaded_images:
            return super().form_valid(form)

        mod_id = self.get_mod().id
        for img in uploaded_images:
            upload_image(img, mod_id=mod_id)

        # empty form when re-rendering this step after successful upload
        return self.render_to_response(self.get_context_data(form=self.get_form_class()()))
    
class ModCreateDescription(UploadStepMixin, UpdateView):
    """
    Mod Creation Multi-Step 4: Add Description.
    """

    model = Mod
    form_class = ModDescriptionForm
    template_name = "mods/create/description/base.html"
    previous_step = "mod_create_images"

    def get_success_url(self):
        return reverse("mod_create_description", kwargs={"mod_id": self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        progress_bar = init_context(current_index=4)

        return context | progress_bar

    def form_valid(self, form):
        response = super().form_valid(form)
        for img in self.object.description_images.all():
            if img.image.url not in (self.object.description or ""):
                img.delete()
        return response

def upload_step3(request):

    return render(
        request,
        "mods/create/step/3.html",
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

        return HttpResponse(status=204)


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

