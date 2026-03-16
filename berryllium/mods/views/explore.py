from django.shortcuts import render

def mods(request):
    """
    Query list of available mods.
    """
    return render(request, "mods/explore/base.html")
