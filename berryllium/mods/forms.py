import os
from django import forms
from django.forms import formset_factory

# from django.core.exceptions import ValidationError
from ..shared.widgets import PillCheckboxSelectMultiple
from .models import FileUpload

ALLOWED_EXTENSIONS = [".z2f", ".ztd", ".zip"]
ILLEGAL_CHARACTERS = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_SUMMARY_LENGTH = 200

ALLOWED_EXTENSIONS = [".z2f", ".ztd", ".zip"]
ILLEGAL_CHARACTERS = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


class MetadataForm(forms.Form):
    """
    This is Step 1 of the file upload form and has simple meta data
    fields like title and description. The group_index and file_order fields are hidden
    and handled in the view.
    """

    title = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "zb-input text-sm", "placeholder": "Enter title"}
        ),
    )
    summary = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"class": "zb-textarea text-sm", "rows": 4}),
    )
    category = forms.MultipleChoiceField(
        choices=[
            ("animals", "Animals"),
            ("animal_needs", "Animal Needs"),
            ("props_and_structures", "Props & Structures"),
            ("packs", "Packs"),
            ("utilities", "Utilities"),
            ("texture_variants", "Texture Variants"),
            ("texture_replacements", "Texture Replacements"),
            ("gameplay_tweaks", "Gameplay Tweaks"),
            ("remakes", "Remakes"),
            ("scripts", "Scripts"),
            ("zoos_and_saves", "Zoos & Saves"),
            ("assets", "Assets"),
        ],
        widget=PillCheckboxSelectMultiple(),
    )
    game = forms.MultipleChoiceField(
        choices=[
            ("na", "Not Applicable"),
            ("zt1", "Zoo Tycoon 1"),
            ("zt2", "Zoo Tycoon 2"),
        ],
        widget=PillCheckboxSelectMultiple(),
    )
    expansions = forms.MultipleChoiceField(
        required=True,
        choices=[
            ("none", "None"),
            ("mm1", "Marine Mania"),
            ("dd", "Dinosaur Digs"),
            ("aa", "African Adventure"),
            ("es", "Endangered Species"),
            ("mm2", "Marine Mania 2"),
            ("ea", "Extinct Animals"),
        ],
        widget=PillCheckboxSelectMultiple(),
    )

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if any(char in title for char in ILLEGAL_CHARACTERS):
            raise forms.ValidationError(
                f"Title contains illegal characters: {', '.join(ILLEGAL_CHARACTERS)}"
            )
        return title

    def clean_summary(self):
        summary = self.cleaned_data.get("summary")
        if len(summary) < 10:
            raise forms.ValidationError("Summary must be at least 10 characters long.")
        if len(summary) > MAX_SUMMARY_LENGTH:
            raise forms.ValidationError(
                f"Summary cannot exceed {MAX_SUMMARY_LENGTH} characters."
            )
        return summary


class FileUploadForm(forms.Form):
    """
    This is Step 2 of the file upload form, which handles
    the actual file upload and validation.
    """

    file = forms.FileField(
        widget=forms.FileInput(attrs={"class": "hidden", "accept": ".z2f,.ztd,.zip"}),
        required=False,
    )

    file_url = forms.URLField(
        widget=forms.URLInput(
            attrs={
                "class": "zb-input text-sm",
                "placeholder": "https://example.com/modfile/",
            }
        ),
        required=False,
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
        """
        Form validation and cleanup.
        """
        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            return None

        # Validate file size
        if uploaded_file.size > MAX_FILE_SIZE:
            raise forms.ValidationError(
                f"File size exceeds the limit of {MAX_FILE_SIZE // (1024 * 1024)} MB."
            )

        # Validate file extension
        if not self.valid_file_extension(uploaded_file.name, ALLOWED_EXTENSIONS):
            raise forms.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Check for illegal characters in filename
        if any(char in uploaded_file.name for char in ILLEGAL_CHARACTERS):
            raise forms.ValidationError(
                f"Filename contains illegal characters: {', '.join(ILLEGAL_CHARACTERS)}"
            )

        if uploaded_file.size == 0:
            raise forms.ValidationError("The uploaded file is empty.")

        return uploaded_file


class FileGroupForm(forms.Form):
    """
    Step 3 of the file upload form, which handles the file organization
    into groups.
    """

    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Group name (e.g., Main Files)",
                "class": "bg-transparent text-white font-medium w-full focus:outline-none",
            }
        ),
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Group description (optional)",
                "class": "zb-textarea",
            }
        ),
    )
    order = forms.IntegerField(widget=forms.HiddenInput(), initial=0)


class FileDetailsForm(forms.ModelForm):
    group_index = forms.IntegerField(widget=forms.HiddenInput())
    file_order = forms.IntegerField(widget=forms.HiddenInput(), initial=0)

    class Meta:
        model = FileUpload
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "File title",
                    "class": "bg-transparent text-white text-sm w-full focus:outline-none",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "placeholder": "File description (optional)",
                    "rows": 2,
                    "class": "zb-textarea",
                }
            ),
        }


FileGroupFormSet = formset_factory(FileGroupForm, extra=0, can_delete=True)
