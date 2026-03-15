from django import forms 
import os
from django.core.exceptions import ValidationError
from core.widgets import PillCheckboxSelectMultiple

ALLOWED_EXTENSIONS = ['.z2f', '.ztd', '.zip']
ILLEGAL_CHARACTERS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_SUMMARY_LENGTH = 200

ALLOWED_EXTENSIONS = ['.z2f', '.ztd', '.zip']
ILLEGAL_CHARACTERS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

class FileUploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'accept': '.z2f,.ztd,.zip'
        }),
        required=False
    )

    def __init__(self, *args, existing_files=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_files = existing_files or []
    
    def valid_file_extension(self, filename, allowed_extensions):
        """Validate file extension"""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            return False
        return True
    
    def clean_file(self):
        if self.existing_files:
                return None  # If there are existing files, no need to validate this field
        
        uploaded_file = self.cleaned_data.get('file')

        if not uploaded_file:
            return None
        
        # Validate file size
        if uploaded_file.size > MAX_FILE_SIZE:
            raise forms.ValidationError(f"File size exceeds the limit of {MAX_FILE_SIZE // (1024*1024)} MB.")
        
        # Validate file extension
        if not self.valid_file_extension(uploaded_file.name, ALLOWED_EXTENSIONS):
            raise forms.ValidationError(f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")
        
        # Check for illegal characters in filename
        if any(char in uploaded_file.name for char in ILLEGAL_CHARACTERS):
            raise forms.ValidationError(f"Filename contains illegal characters: {', '.join(ILLEGAL_CHARACTERS)}")
        
        if uploaded_file.size == 0:
            raise forms.ValidationError("The uploaded file is empty.")
        
        return uploaded_file
