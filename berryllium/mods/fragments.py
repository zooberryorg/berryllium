from berryllium.mods.forms import FileUploadForm
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from django.shortcuts import render

def validate_url_field(file_url):
    """HTMX endpoint to validate file URL field."""
    form = FileUploadForm()
    form.fields['file_url'].validators = [URLValidator(schemes=["http", "https"])]
    try:
        form.fields['file_url'].clean(file_url)
        return render(None, 'mods/upload/partials/file_url_valid.html')
    except ValidationError:
        return render(None, 'mods/upload/partials/file_url_invalid.html')