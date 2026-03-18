from berryllium.mods.forms import FileUploadForm
from berryllium.mods.models import Mod
from django.shortcuts import render, HttpResponse
from django.views.decorators.http import require_POST

@require_POST
def process_url_field(request):
    """HTMX endpoint to validate file URL field."""
    file_url = request.POST.get("file_url", "")

    # save url field when cleared
    if file_url == "":
        mod_id = request.session.get("mod_id")
        if mod_id:
            mod = Mod.objects.filter(id=mod_id).first()
            if mod:
                mod.external_url = ""
                mod.is_external = False
                mod.save()
                return HttpResponse()
            
    # handle dynamic validation
    form = FileUploadForm(data={"file_url": file_url})
    form.is_valid()
    if form.errors.get("file_url"):
        error_message = form.errors["file_url"][0]
        return render(request, "mods/fragments/file_url_error.html", {"error_message": error_message})
    
    return HttpResponse()