from django.shortcuts import render

# Create your views here.

def upload_mod(request):
    return render(request, 'mods/upload/base.html')