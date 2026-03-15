from django.shortcuts import render
from ..forms import FileUploadForm

# Create your views here.


def upload_mod(request):
    """
    Landing page for mod upload requests.
    """
    return render(request, "mods/upload/base.html")


def upload_step1(request):
    """
    Step 1 of the upload form.
    """
    return render(request, "mods/upload/step/1.html")
