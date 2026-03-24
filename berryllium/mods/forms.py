import os
from django import forms
from django.forms import formset_factory, Textarea, TextInput, CheckboxSelectMultiple
from django.core.validators import (
    URLValidator,
    MaxLengthValidator,
    MinLengthValidator,
    FileExtensionValidator,
    ProhibitNullCharactersValidator,
)
from django.core.exceptions import ValidationError

# from django.core.exceptions import ValidationError
from berryllium.shared.widgets import PillCheckboxSelectMultiple
from berryllium.mods.models import FileUpload, FileGroup
from berryllium.mods.models import Mod
from berryllium.mods.settings import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    ILLEGAL_CHARACTERS,
    MIN_TEXTFIELD_LENGTH,
    MAX_TEXTFIELD_LENGTH,
    MIN_SUMMARY_LENGTH,
    MAX_SUMMARY_LENGTH,
    COLLAPSIBLE_WIDGET_ATTRS,
    DISABLE_SUBMIT_BUTTON_ATTRS,
    MOD_CATEGORIES,
    GAME_OPTIONS,
    EXPANSION_REQUIREMENTS,
)


class ModCategoriesForm(forms.ModelForm):
    """
    This is Step 1 of the file upload form and has simple meta data
    fields like title and summary. The group_index and file_order fields are hidden
    and handled in the view.
    """

    class Meta:
        model = Mod
        fields = ["title", "summary", "category", "game", "expansions"]
        widgets = {
            "title": TextInput(
                attrs={
                    "placeholder": "Group name (e.g., Main Files)",
                    "class": "zb-input text-sm",
                    "autocomplete": "off",
                    **DISABLE_SUBMIT_BUTTON_ATTRS,
                },
            ),
        }
    
    field_order = ["title", "summary", "category", "game", "expansions"]

    summary = forms.CharField(
        required=True,
        widget=Textarea(attrs={
            "placeholder": "Enter a brief summary...",
            "class": "zb-textarea text-sm",
            **COLLAPSIBLE_WIDGET_ATTRS,
        }),
    )
    
    category = forms.MultipleChoiceField(
        choices=MOD_CATEGORIES,
        widget=PillCheckboxSelectMultiple(
            attrs={
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )
    game = forms.MultipleChoiceField(
        choices=GAME_OPTIONS,
        widget=PillCheckboxSelectMultiple(
            attrs={
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )
    expansions = forms.MultipleChoiceField(
        required=True,
        choices=EXPANSION_REQUIREMENTS,
        widget=PillCheckboxSelectMultiple(
            attrs={
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
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
        if len(summary) < MIN_TEXTFIELD_LENGTH:
            raise forms.ValidationError(
                f"Summary must be at least {MIN_TEXTFIELD_LENGTH} characters long."
            )
        if len(summary) > MAX_SUMMARY_LENGTH:
            raise forms.ValidationError(
                f"Summary cannot exceed {MAX_SUMMARY_LENGTH} characters."
            )
        return summary
    
    def multiple_choice_clean(self, field_name):
        choices = self.cleaned_data.get(field_name)
        if not choices:
            raise forms.ValidationError(f"Please select at least one option for {field_name}.")
        return ", ".join(choices)
    
    def clean_category(self):
        return self.multiple_choice_clean("category")

    def clean_game(self):
        return self.multiple_choice_clean("game")
    
    def clean_expansions(self):
        return self.multiple_choice_clean("expansions")

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

    def clean_file(self):
        """
        Form validation and cleanup.
        """
        cleaned_file = self.cleaned_data.get("file")
        cleaned_file.__str__

        # if no file uploaded, check if file URL is provided, if not raise error
        if not cleaned_file:
            return cleaned_file
        print(
            "Validating uploaded file:", cleaned_file.name, cleaned_file.size, "bytes"
        )
        # Validate file extension
        try:
            FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)(cleaned_file)
        except ValidationError:
            raise forms.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Validate file size
        if cleaned_file.size > MAX_FILE_SIZE:
            raise forms.ValidationError(
                f"File size exceeds the maximum limit of {MAX_FILE_SIZE // (1024 * 1024)} MB."
            )

        # Check for illegal characters in filename
        if any(char in cleaned_file.name for char in ILLEGAL_CHARACTERS):
            raise forms.ValidationError(
                f"Filename contains illegal characters: {', '.join(ILLEGAL_CHARACTERS)}"
            )

        if cleaned_file.size == 0:
            raise forms.ValidationError("The uploaded file is empty.")

        return cleaned_file

    def clean_file_url(self):
        """
        Validate the file URL field.
        """
        file_url = self.cleaned_data.get("file_url")

        # if no url provided, skip validation (file upload will be validated in clean_file)
        if not file_url:
            return file_url

        # Validate URL format
        try:
            URLValidator(schemes=["http", "https"])(file_url)
        except ValidationError:
            raise forms.ValidationError(
                "Please enter a valid URL. Protocol (http:// or https://) is required."
            )

        return file_url

    # cross-field validation to ensure either file or file_url is provided
    def clean(self):
        cleaned_data = super().clean()
        cleaned_file = cleaned_data.get("file")
        file_url = cleaned_data.get("file_url")

        # only one of file or file_url can be provided, not both
        if (cleaned_file or self.existing_files) and file_url:
            raise forms.ValidationError(
                "Only one of file upload or file URL can be provided. Please choose one."
            )

        # in case absolutely nothing has been input
        if not cleaned_file and not file_url and not self.existing_files:
            raise forms.ValidationError("Please upload a file or provide a file URL.")

        return cleaned_data


class FileGroupForm(forms.ModelForm):
    """
    Step 3 of the file upload form, which handles the file organization
    into groups.
    """

    # note: fields here need to match the fields in the FileGroup model
    class Meta:
        model = FileGroup
        fields = ["name", "description"]
        help_texts = {
            "name": "Name of the file group (e.g., Main Files, etc.)",
            "description": "Optional description for this file group.",
        }

    name = forms.CharField(
        required=False,
        max_length=MAX_TEXTFIELD_LENGTH,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Group name (e.g., Main Files)",
                "class": "pl-2 py-1 mr-24 text-sm text-white/80 focus:outline-none min-w-0 rounded-xl hover:bg-gold-400/10",
                "autocomplete": "off",
            }
        ),
    )
    description = forms.CharField(
        max_length=MAX_SUMMARY_LENGTH,
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": "Enter group description",
                "x-ref": "collapsibleGroupDesc",
                "class": "px-2 py-1 mt-2 text-sm text-white/80 focus:outline-none w-full rounded-xl hover:bg-gold-400/10 resize-none transition-all duration-200 ",
                **COLLAPSIBLE_WIDGET_ATTRS,
            }
        ),
    )
    order = forms.IntegerField(widget=forms.HiddenInput(), initial=0)

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()

        if len(name) == 0:
            return None

        try:
            MinLengthValidator(MIN_TEXTFIELD_LENGTH)(name)
        except ValidationError:
            raise forms.ValidationError(
                f"Group name must be at least {MIN_TEXTFIELD_LENGTH} characters long."
            )
        try:
            MaxLengthValidator(MAX_TEXTFIELD_LENGTH)(name)
        except ValidationError:
            raise forms.ValidationError(
                f"Group name cannot exceed {MAX_TEXTFIELD_LENGTH} characters."
            )
        try:
            ProhibitNullCharactersValidator()(name)
        except ValidationError:
            raise forms.ValidationError("Group name cannot contain null characters.")

        return name

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()

        if len(description) == 0:
            return None

        try:
            MinLengthValidator(MIN_SUMMARY_LENGTH)(description)
        except ValidationError:
            raise forms.ValidationError(
                f"Group description must be at least {MIN_SUMMARY_LENGTH} characters long."
            )
        try:
            MaxLengthValidator(MAX_SUMMARY_LENGTH)(description)
        except ValidationError:
            raise forms.ValidationError(
                f"Group description cannot exceed {MAX_SUMMARY_LENGTH} characters."
            )
        try:
            ProhibitNullCharactersValidator()(description)
        except ValidationError:
            raise forms.ValidationError(
                "Group description cannot contain null characters."
            )

        return description


class SingleFileForm(forms.Form):
    """
    This form is for editing single files within a FileGroup.
    """

    title = forms.CharField(
        required=False,
        max_length=MAX_TEXTFIELD_LENGTH,
        widget=forms.TextInput(
            attrs={
                "placeholder": "File title",
                "class": "bg-transparent text-white text-sm w-full focus:outline-none",
            }
        ),
    )
    description = forms.CharField(
        max_length=MAX_SUMMARY_LENGTH,
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": "File description (optional)",
                "class": "zb-textarea transition-all duration-200",
                **COLLAPSIBLE_WIDGET_ATTRS,
            }
        ),
    )

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        print("Validating title:", title)

        if len(title) == 0:
            return None

        try:
            MinLengthValidator(MIN_TEXTFIELD_LENGTH)(title)
        except ValidationError:
            raise forms.ValidationError(
                f"File title must be at least {MIN_TEXTFIELD_LENGTH} characters long."
            )
        try:
            MaxLengthValidator(MAX_TEXTFIELD_LENGTH)(title)
        except ValidationError:
            raise forms.ValidationError(
                f"File title cannot exceed {MAX_TEXTFIELD_LENGTH} characters."
            )
        try:
            ProhibitNullCharactersValidator()(title)
        except ValidationError:
            raise forms.ValidationError("File title cannot contain null characters.")

        return title

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()
        print("Validating description:", description)

        if len(description) == 0:
            return None

        try:
            MinLengthValidator(MIN_SUMMARY_LENGTH)(description)
        except ValidationError:
            raise forms.ValidationError(
                f"File description must be at least {MIN_SUMMARY_LENGTH} characters long."
            )
        try:
            MaxLengthValidator(MAX_SUMMARY_LENGTH)(description)
        except ValidationError:
            raise forms.ValidationError(
                f"File description cannot exceed {MAX_SUMMARY_LENGTH} characters."
            )
        try:
            ProhibitNullCharactersValidator()(description)
        except ValidationError:
            raise forms.ValidationError(
                "File description cannot contain null characters."
            )

        return description


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
