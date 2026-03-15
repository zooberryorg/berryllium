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
    current_index = 1
    progress_range = range(current_index)
    remainder_range = range(current_index, len(NAVIGATION))
    nav_item_count = len(NAVIGATION)
    context = {
        'form': MetadataForm(),
        'filename': request.session.get('upload_original_name'),
        'nav_item_count': nav_item_count,
        'current_nav_index': 0,
        'progress_range': progress_range,
        'remainder_range': remainder_range,
    }

    if request.method == 'POST':
        form = MetadataForm(request.POST)
        if form.is_valid():
            # Store metadata in session
            request.session['upload_metadata'] = form.cleaned_data
            
            # Return NEXT state (step 2) on success
            return redirect('create_mods_step2')
        
        # Invalid: return SAME state with errors
        context['form'] = form
        return render(request, 'mods/upload/step/1.html', context=context)
    elif request.method == 'GET' and request.session.get('upload_metadata'):
        # Send existing files for review at form initialization TODO: simply send a boolean
        form = MetadataForm(initial=request.session['upload_metadata'])
        context['form'] = form
        return render(request, 'mods/upload/step/1.html', context=context)
        
    # GET: show fresh form
    return render(request, 'mods/upload/step/1.html', context=context)

def upload_step2(request):
    """
    Step 2 of the upload form.
    """
    return render(request, "mods/upload/step/1.html")