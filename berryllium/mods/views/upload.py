from django.shortcuts import render
from ..forms import FileUploadForm

# Navigation configuration for upload form
#     name: Current location title
#     url: Reference Django url
#     icon: Icon name. See: https://icons.getbootstrap.com/
NAVIGATION = [
    {'name': 'Basic Information', 'url': 'upload_step1', 'icon': 'info-circle'},
    # {'name': 'Upload Files', 'url': 'create_mods_step2', 'icon': 'upload'},
    # {'name': 'Organize Files', 'url': 'create_mods_step3', 'icon': 'folder'},
    # {'name': 'Review & Submit', 'url': 'create_mods_step4', 'icon': 'check-circle'},
]

def upload_mod(request):
    """
    Landing page for mod upload requests.
    """
    return render(request, "mods/upload/base.html", {
        'form': FileUploadForm(),
        'mod_navigation': NAVIGATION,
    })



def upload_step1(request):
    """
    Step 1 of the upload form.
    """
    return render(request, "mods/upload/step/1.html")
