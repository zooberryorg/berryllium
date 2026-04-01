from django import forms
from django.forms import formset_factory, Textarea, TextInput
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    FileExtensionValidator,
    ProhibitNullCharactersValidator,
)
from django.core.exceptions import ValidationError

# from django.core.exceptions import ValidationError
from berryllium.shared.widgets import PillCheckboxSelectMultiple
from berryllium.mods.models import ModFile, ModFileGroup
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
    MAX_IMAGE_SIZE,
)

from markdownx.fields import MarkdownxFormField
from markdownx.widgets import MarkdownxWidget


class ModGeneralInfoForm(forms.ModelForm):
    """
    Handles the general information about the mod like title, summary, ownership, publication date, etc.
    """

    summary = forms.CharField(
        required=True,
        widget=Textarea(
            attrs={
                "placeholder": "Enter a brief summary...",
                "class": "zb-textarea text-sm resize-none",
                "rows": 4,
            }
        ),
    )

    class Meta:
        model = Mod
        fields = ["title", "summary"]
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

        # clean summary of leading/trailing whitespace and null characters
        summary = summary.strip()
        return summary

class ModCategorizationForm(forms.ModelForm):
    """
    This is Step 1 of the file upload form and has simple meta data
    fields like title and summary.
    """

    def multiple_choice_attributes(choices, widget_class):
        return forms.MultipleChoiceField(
            choices=choices,
            widget=widget_class(
                attrs={
                    **DISABLE_SUBMIT_BUTTON_ATTRS,
                }
            ),
        )

    category = multiple_choice_attributes(MOD_CATEGORIES, PillCheckboxSelectMultiple)
    game = multiple_choice_attributes(GAME_OPTIONS, PillCheckboxSelectMultiple)
    expansions = multiple_choice_attributes(
        EXPANSION_REQUIREMENTS, PillCheckboxSelectMultiple
    )

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

        # clean summary of leading/trailing whitespace and null characters
        summary = summary.strip()
        return summary

    def multiple_choice_clean(self, field_name):
        choices = self.cleaned_data.get(field_name)
        if not choices:
            raise forms.ValidationError(
                f"Please select at least one option for {field_name}."
            )
        return ", ".join(choices)

    def clean_category(self):
        return self.multiple_choice_clean("category")

    def clean_game(self):
        return self.multiple_choice_clean("game")

    def clean_expansions(self):
        return self.multiple_choice_clean("expansions")


class ModFileGroupForm(forms.ModelForm):
    """
    Step 3 of the file upload form, which handles the file organization
    into groups.
    """

    # note: fields here need to match the fields in the ModFileGroup model
    class Meta:
        model = ModFileGroup
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


class ModFileForm(forms.Form):
    """
    This form is for editing single files within a ModFileGroup.
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


class ModFileUploadForm(forms.Form):
    """
    This is Step 2 of the file upload form, which handles
    the actual file upload and validation.
    """

    file = forms.FileField(
        widget=forms.FileInput(attrs={"class": "hidden", "accept": ".z2f,.ztd,.zip"}),
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

        # no files uploaded or existing
        if cleaned_file.size == 0 and len(self.existing_files) == 0:
            raise forms.ValidationError("Please upload a file before proceeding.")

        if cleaned_file.size == 0:
            raise forms.ValidationError("The uploaded file is empty.")

        return cleaned_file


class MultipleFileInput(forms.FileInput):
    """
    Custom widget to allow multiple file uploads.
    """

    allow_multiple_selected = True


class MultipleImageInputField(forms.ImageField):
    """
    Custom form field to handle multiple image uploads.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file(d, initial) for d in data]
        return single_file(data, initial)


class ModImageUploadForm(forms.Form):
    """
    This is Step 3 of the file upload form, which handles
    the picture upload and validation.
    """

    image = MultipleImageInputField(
        required=False,
    )

    def __init__(self, *args, existing_images=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_images = existing_images or []

    def clean_image(self):
        images = self.files.getlist("image")
        print("Validating uploaded images:", [img.name for img in images])
        if not images:
            return None

        # ------------------ clean each image and validate
        cleaned_images = []

        # Validate image size
        for img in images:
            if img.size > MAX_IMAGE_SIZE:
                raise forms.ValidationError(
                    f"Image size exceeds the maximum limit of {MAX_IMAGE_SIZE // (1024 * 1024)} MB."
                )

            if img.size == 0:
                raise forms.ValidationError("The uploaded image is empty.")

            # Check for illegal characters in filename
            if any(char in img.name for char in ILLEGAL_CHARACTERS):
                raise forms.ValidationError(
                    f"Filename contains illegal characters: {', '.join(ILLEGAL_CHARACTERS)}"
                )

            if img.name in [img["filename"] for img in self.existing_images]:
                # rename file by appending a number to the end of the filename
                base_name, extension = img.name.rsplit(".", 1)
                counter = 1
                while f"{base_name}_{counter}.{extension}" in [
                    img["filename"] for img in self.existing_images
                ]:
                    counter += 1

            cleaned_images.append(img)

        return cleaned_images


class ModImageForm(forms.Form):
    """
    This form is for editing single images within the mod creation process.
    """

    caption = forms.CharField(
        required=False,
        max_length=MAX_TEXTFIELD_LENGTH,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Image caption",
                "class": "bg-transparent text-white text-sm w-full focus:outline-none",
            }
        ),
    )

    def clean_caption(self):
        caption = self.cleaned_data.get("caption", "").strip()

        if len(caption) == 0:
            return None

        try:
            MinLengthValidator(MIN_TEXTFIELD_LENGTH)(caption)
        except ValidationError:
            raise forms.ValidationError(
                f"Image caption must be at least {MIN_TEXTFIELD_LENGTH} characters long."
            )
        try:
            MaxLengthValidator(MAX_TEXTFIELD_LENGTH)(caption)
        except ValidationError:
            raise forms.ValidationError(
                f"Image caption cannot exceed {MAX_TEXTFIELD_LENGTH} characters."
            )
        try:
            ProhibitNullCharactersValidator()(caption)
        except ValidationError:
            raise forms.ValidationError("Image caption cannot contain null characters.")

        return caption


class ModDescriptionForm(forms.ModelForm):
    """
    This is Step 4 of the mod creation form, which handles the detailed
    description and other metadata.
    """

    description = MarkdownxFormField(
        required=False,
        widget=MarkdownxWidget(
            attrs={
                "placeholder": "Enter detailed description...",
                "class": "zb-textarea text-sm resize-none",
                "rows": 6,
            }
        ),
    )

    class Meta:
        model = Mod
        fields = ["description"]


ModFileGroupFormSet = formset_factory(ModFileGroupForm, extra=0, can_delete=True)
