from berryllium.mods.models import Mod

from django.shortcuts import render, HttpResponse
from django.views.decorators.http import require_POST
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

@require_POST
def process_url_field(request):
    """HTMX endpoint to validate file URL field."""
    file_url = request.POST.get("file_url", "")
    # save url field when cleared
    if not file_url:
        mod_id = request.session.get("session_id")
        if mod_id:
            mod = Mod.objects.filter(id=mod_id).first()
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
        error_message = "Please enter a valid URL. Protocol (http:// or https://) is required."
        return render(
            request, "mods/upload/step/partials/hx_errors.html", {"error_message": error_message}
        )

    # if valid, return empty response
    return HttpResponse()
