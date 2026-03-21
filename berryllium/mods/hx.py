from berryllium.mods.models import Mod
from berryllium.mods.models import FileUpload

from django.shortcuts import render, HttpResponse
from django.views.decorators.http import require_POST
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


@require_POST
def hx_process_url_field(request):
    """HTMX endpoint to validate file URL field."""
    file_url = request.POST.get("file_url", "")
    mod_id = request.session.get("session_id")

    # shouldn't really happen unless session is lost
    if not mod_id:
        return HttpResponse(status=400)

    mod = Mod.objects.filter(id=mod_id).first()
    # save url field when cleared
    if not file_url:
        if mod:
            mod.external_url = ""
            mod.is_external = False
            mod.save()
        # return empty response to clear any existing errors
        return HttpResponse()

    # handle dynamic validation
    try:
        URLValidator(schemes=["http", "https"])(file_url)
    except ValidationError:
        error_message = (
            "Please enter a valid URL. Protocol (http:// or https://) is required."
        )
        return render(
            request,
            "mods/upload/step/partials/hx_errors.html",
            {"error_message": error_message},
        )

    # if valid, save to mod draft
    if mod:
        mod.external_url = file_url
        mod.is_external = True
        mod.save()

    # if valid, return empty response
    return HttpResponse()


@require_POST
def hx_toggle_group_manager(request):
    """HTMX endpoint to toggle file group manager visibility."""
    isToggled = "group_manager_toggle" in request.POST
    request.session["group_manager_toggled"] = isToggled
    return HttpResponse()


@require_POST
def hx_validate_file_title(request, file_id):
    """HTMX endpoint to validate file title field."""
    title = request.POST.get("title", "")

    if len(title) > 100:
        error_message = "Title cannot exceed 100 characters."
        return render(
            request,
            "mods/upload/step/partials/hx_errors.html",
            {"error_message": error_message},
        )

    # if valid, save to FileUpload draft
    file_upload = FileUpload.objects.filter(id=file_id).first()
    if file_upload:
        file_upload.title = title
        file_upload.save()

    return HttpResponse()
