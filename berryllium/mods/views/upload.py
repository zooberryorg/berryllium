from django.shortcuts import render

# Create your views here.


def upload_mod(request):
    """
    Landing page for mod upload requests.
    """
    return render(request, "mods/upload/base.html")

