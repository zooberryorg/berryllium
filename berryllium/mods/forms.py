from django import forms
from django.forms import formset_factory, Textarea, TextInput
from datetime import date
from django.utils import timezone
from django.core.validators import (
    MaxLengthValidator,
    MinLengthValidator,
    FileExtensionValidator,
    ProhibitNullCharactersValidator,
)
from django.core.exceptions import ValidationError
from django.urls import reverse

from berryllium.mods.models import ModCredit
from berryllium.mods.pickers import (
    PickerField,
    picker_config,
    resolve_people,
    people_items,
    credits_as_resolved,
    save_credits,
    website_items_from_values,
    website_item,
    resolve_tags,
    tag_items,
    save_tags,
)
from berryllium.shared.models import ArchivedWebsite, Language, License
from berryllium.shared.fields import JSONRowsField, raw_rows
from berryllium.shared.links import LINK_PRESETS, DEFAULT_LINK_PRESET
from berryllium.mods.resources import (
    clean_dependency_row,
    clean_license_row,
    clean_attribution_row,
    clean_link_row,
    dependency_rows,
    license_rows,
    attribution_rows,
    link_rows,
    widget_config,
    save_resources,
)
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
    MOD_THUMBNAIL_MIN_SIZE,
    MOD_THUMBNAIL_RECOMMENDED_SIZE,
)


class ModGeneralInfoForm(forms.ModelForm):
    """
    Handles the general information about the mod like title, summary, ownership, publication date, etc.
    """

    title = forms.CharField(
        required=True,
        widget=TextInput(
            attrs={
                "placeholder": "Enter mod title...",
                "class": "zb-input text-sm",
                "autocomplete": "off",
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )

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

    collaborators = PickerField(
        required=False,
        allow_new=True,
        label="Collaborators",
        help_text="People who made this mod with you.",
    )

    original_authors = PickerField(
        required=False,
        allow_new=True,
        label="Original Authors",
        help_text="Who made the mod originally.",
    )

    original_websites = forms.ModelMultipleChoiceField(
        queryset=ArchivedWebsite.objects.filter(is_enabled=True),
        required=False,
        label="Original Websites",
        widget=forms.MultipleHiddenInput,
    )

    thumbnail = forms.ImageField(
        required=True,
        label="Thumbnail / Logo",
        help_text=(
            f"Square (1:1), {MOD_THUMBNAIL_RECOMMENDED_SIZE} recommended, "
            f"at least {MOD_THUMBNAIL_MIN_SIZE}px. JPG, PNG or WEBP."
        ),
        widget=forms.FileInput(
            attrs={
                "accept": ".jpg,.jpeg,.png,.webp",
                "class": "hidden",
                "x-ref": "thumbInput",
                "@change": "preview($event)",
            }
        ),
    )

    publish_date = forms.DateTimeField(required=True, widget=forms.HiddenInput)

    is_archived_file = forms.BooleanField(
        required=False,
        label="Is this an archived mod?",
        widget=forms.CheckboxInput(attrs={"class": "sr-only peer", "x-model": "archived"}),
    )

    original_release_date = forms.DateField(
        required=False,
        label="Original release date",
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "class": "zb-input text-sm", ":disabled": "!archived"},
        ),
    )

    class Meta:
        model = Mod
        fields = [
            "title", "summary", "thumbnail", "publish_date",
            "is_archived_file", "original_release_date", "original_websites",
        ]
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

        summary = summary.strip()
        return summary

    def __init__(self, *args, uploader=None, **kwargs):
        super().__init__(*args, **kwargs)
        # the uploader is always the first, locked collaborator
        self.uploader = uploader or self.instance.uploaded_by        
        # the date picker can't go past today
        self.fields["original_release_date"].widget.attrs["max"] = date.today().isoformat()

    def publish_date_iso(self):
        """Publication date as ISO 8601 with timezone, for the date picker script."""
        if self.is_bound:
            return self.data.get("publish_date", "")
        value = self.initial.get("publish_date") or self.instance.publish_date or timezone.now()
        return value.isoformat()

    def clean_thumbnail(self):
        thumb = self.cleaned_data.get("thumbnail")
        # editing without choosing a new file: keep the existing one
        if not thumb or not hasattr(thumb, "image"):
            return thumb
        if thumb.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError(f"Thumbnail must be under {MAX_IMAGE_SIZE // (1024 * 1024)} MB.")
        if thumb.image.format not in ("JPEG", "PNG", "WEBP"):
            raise forms.ValidationError("Thumbnail must be a JPG, PNG or WEBP image.")
        width, height = thumb.image.size
        if width < MOD_THUMBNAIL_MIN_SIZE or height < MOD_THUMBNAIL_MIN_SIZE:
            raise forms.ValidationError(
                f"Thumbnail must be at least {MOD_THUMBNAIL_MIN_SIZE}×{MOD_THUMBNAIL_MIN_SIZE}px "
                f"(yours is {width}×{height})."
            )
        return thumb

    def clean_original_release_date(self):
        value = self.cleaned_data.get("original_release_date")
        if value and value > date.today():
            raise forms.ValidationError("The original release date can't be in the future.")
        return value

    def clean_collaborators(self):
        return resolve_people(self.cleaned_data.get("collaborators", []))

    def clean_original_authors(self):
        return resolve_people(self.cleaned_data.get("original_authors", []))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_archived_file"):
            if not cleaned.get("original_release_date"):
                self.add_error("original_release_date", "Required for archived mods.")
            if not cleaned.get("original_websites"):
                self.add_error("original_websites", "Pick at least one website.")
            if not cleaned.get("original_authors"):
                self.add_error("original_authors", "Add at least one original author.")
        else:
            # don't keep stale archive info
            cleaned["original_release_date"] = None
            cleaned["original_websites"] = ArchivedWebsite.objects.none()
            cleaned["original_authors"] = []
        return cleaned


    def save_relations(self):
        """Save credits. Call after the mod itself has been saved."""
        mod = self.instance
        if not self.cleaned_data.get("is_archived_file"):
            save_credits(
                mod, ModCredit.Role.COLLABORATOR, self.cleaned_data["collaborators"], uploader=self.uploader
            )
        elif self.uploader and not mod.credits.filter(role=ModCredit.Role.COLLABORATOR).exists():

            save_credits(mod, ModCredit.Role.COLLABORATOR, [], uploader=self.uploader)
        save_credits(mod, ModCredit.Role.ORIGINAL_AUTHOR, self.cleaned_data["original_authors"])

    # -------- picker pills: after data is submitted after an error comes up

    def _submitted(self, name):
        return [v for v in self.data.getlist(self.add_prefix(name)) if v]

    def _people(self, name, role):
        if self.is_bound:
            return resolve_people(self._submitted(name), strict=False)
        if self.instance.pk:
            return credits_as_resolved(self.instance, role)
        return []

    def collaborators_picker(self):
        return picker_config(
            name=self.add_prefix("collaborators"),
            search_url=reverse("search_people"),
            items=people_items(self._people("collaborators", ModCredit.Role.COLLABORATOR), uploader=self.uploader),
            title="Add collaborators",
            placeholder="Search members by name...",
            allow_new=True,
        )

    def original_authors_picker(self):
        return picker_config(
            name=self.add_prefix("original_authors"),
            search_url=reverse("search_people"),
            items=people_items(self._people("original_authors", ModCredit.Role.ORIGINAL_AUTHOR)),
            title="Add original authors",
            placeholder="Search authors by name...",
            allow_new=True,
        )

    def original_websites_picker(self):
        if self.is_bound:
            items = website_items_from_values(self._submitted("original_websites"))
        elif self.instance.pk:
            items = [website_item(w) for w in self.instance.original_websites.all()]
        else:
            items = []
        return picker_config(
            name=self.add_prefix("original_websites"),
            search_url=reverse("search_websites"),
            items=items,
            title="Add original websites",
            placeholder="Search archived websites...",
            empty_text="No matching websites. Ask staff to add it if it's missing.",
        )

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
    tags = PickerField(required=False, allow_new=True, max_items=20, label="Tags")

    class Meta:
        model = Mod
        fields = ["category", "game", "expansions"]


    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_tags(self):
        return resolve_tags(self.cleaned_data.get("tags", []))

    def save_relations(self):
        existing, new_names = self.cleaned_data["tags"]
        save_tags(self.instance, existing, new_names, user=self.user)

    def tags_picker(self):
        if self.is_bound:
            existing, new_names = resolve_tags(
                [v for v in self.data.getlist(self.add_prefix("tags")) if v], strict=False
            )
        else:
            existing = list(self.instance.tags.all()) if self.instance.pk else []
            new_names = list(self.instance.pending_tags or [])
        return picker_config(
            name=self.add_prefix("tags"),
            search_url=reverse("search_tags"),
            items=tag_items(existing, new_names),
            title="Add tags",
            placeholder="Search tags...",
            allow_new=True,
        )

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

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": "Enter detailed description...",
                "class": "zb-textarea text-sm resize-y w-full font-mono",
                "rows": 14,
            }
        ),
    )

    class Meta:
        model = Mod
        fields = ["description"]

class DescriptionImageForm(forms.Form):
    image = forms.ImageField()

    def clean_image(self):
        img = self.cleaned_data["image"]
        if img.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError(f"Images must be under {MAX_IMAGE_SIZE // (1024 * 1024)} MB.")
        if img.image.format not in ("JPEG", "PNG", "WEBP", "GIF"):
            raise forms.ValidationError("Only JPG, PNG, WEBP or GIF images are allowed.")
        return img


ModFileGroupFormSet = formset_factory(ModFileGroupForm, extra=0, can_delete=True)

class ModResourcesForm(forms.ModelForm):
    """
    Step 5 of the upload form: dependencies, licenses, languages, additional credits and links.
    """

    dependencies = JSONRowsField(row_cleaner=clean_dependency_row, required=False, label="Dependencies")
    licenses = JSONRowsField(row_cleaner=clean_license_row, required=False, max_rows=10, label="Licenses")
    attributions = JSONRowsField(row_cleaner=clean_attribution_row, required=False, label="Additional credits")
    links = JSONRowsField(row_cleaner=clean_link_row, required=False, max_rows=20, label="Links")
    languages = forms.ModelMultipleChoiceField(
        queryset=Language.objects.all(),
        required=False,
        label="Languages",
        widget=forms.MultipleHiddenInput,
    )

    class Meta:
        model = Mod
        fields = ["languages"]

    def clean_dependencies(self):
        rows = self.cleaned_data["dependencies"]
        ids = [row["mod"] for row in rows if row["kind"] == "internal"]
        mods = Mod.objects.exclude(pk=self.instance.pk).in_bulk(ids)
        cleaned, seen = [], set()
        for row in rows:
            if row["kind"] == "internal":
                if row["mod"] not in mods:
                    raise forms.ValidationError("One of the selected mods no longer exists. Remove it and try again.")
                if row["mod"] in seen:
                    continue
                seen.add(row["mod"])
                row["mod_obj"] = mods[row["mod"]]
            cleaned.append(row)
        return cleaned

    def clean_licenses(self):
        rows = self.cleaned_data["licenses"]
        licenses = License.objects.filter(is_enabled=True).in_bulk([row["license"] for row in rows])
        for row in rows:
            if row["license"] not in licenses:
                raise forms.ValidationError("One of the selected licenses is no longer available. Remove it and try again.")
            row["license_obj"] = licenses[row["license"]]
        return rows

    def save_relations(self):
        save_resources(
            self.instance,
            dependencies=self.cleaned_data["dependencies"],
            licenses=self.cleaned_data["licenses"],
            attributions=self.cleaned_data["attributions"],
            links=self.cleaned_data["links"],
        )

    # ---- widget configs: submitted rows after an error, otherwise from the database

    def _rows(self, name, from_db):
        if self.is_bound:
            return raw_rows(self.data, self.add_prefix(name))
        return from_db(self.instance) if self.instance.pk else []

    def dependencies_widget(self):
        search_url = reverse("search_mods")
        if self.instance.pk:
            search_url += f"?exclude={self.instance.pk}"
        return widget_config(
            name=self.add_prefix("dependencies"),
            searchUrl=search_url,
            items=self._rows("dependencies", dependency_rows),
            title="Add dependencies",
            placeholder="Search mods...",
            emptyText="No matching mods. Add it as an external dependency instead.",
            insertKind="internal",
            newRow={"context": "", "version": ""},
            allowExternal=True,
            externalLabel="Add external dependency",
            contextLabel="Why it's needed",
            contextPlaceholder="e.g. Required for the new animal behaviors",
            showVersion=True,
        )

    def licenses_widget(self):
        return widget_config(
            name=self.add_prefix("licenses"),
            searchUrl=reverse("search_licenses"),
            items=self._rows("licenses", license_rows),
            title="Add licenses",
            searchLabel="Search licenses",
            placeholder="Search licenses...",
            emptyText="No matching licenses. Ask staff if one is missing.",
            emptyListText="No license chosen.",
            newRow={"context": ""},
            contextPlaceholder='What it covers, e.g. "only the dinosaur texture" (leave empty if it covers everything)',
            showVersion=False,
            sortable=False,
        )

    def attributions_widget(self):
        return widget_config(
            name=self.add_prefix("attributions"),
            rows=self._rows("attributions", attribution_rows),
            blank={"title": "", "url": "", "authors": "", "note": ""},
            addLabel="Add credit",
            emptyText="No additional credits.",
            sortable=True,
        )

    def links_widget(self):
        return widget_config(
            name=self.add_prefix("links"),
            rows=self._rows("links", link_rows),
            blank={"kind": DEFAULT_LINK_PRESET, "url": "", "label": ""},
            addLabel="Add link",
            emptyText="No links.",
            presets=LINK_PRESETS,
            sortable=True,
        )

    def languages_picker(self):
        if self.is_bound:
            ids = [v for v in self.data.getlist(self.add_prefix("languages")) if str(v).isdigit()]
            languages = Language.objects.filter(pk__in=ids)
        else:
            languages = self.instance.languages.all() if self.instance.pk else Language.objects.none()
        return picker_config(
            name=self.add_prefix("languages"),
            search_url=reverse("search_languages"),
            items=[{"value": str(lang.pk), "label": lang.name, "sublabel": lang.code} for lang in languages],
            title="Add languages",
            placeholder="Search languages...",
            empty_text="No matching languages. Ask staff if one is missing.",
        )
