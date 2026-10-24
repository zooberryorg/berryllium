from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from berryllium.mods.resources import clean_link_row, widget_config
from berryllium.mods.settings import MAX_IMAGE_SIZE
from berryllium.organizations.models import Organization, OrganizationLink
from berryllium.shared.fields import JSONRowsField, raw_rows
from berryllium.shared.links import DEFAULT_LINK_PRESET, LINK_PRESETS

INPUT = "zb-input text-sm w-full"
MIN_LOGO_SIZE = 128
MIN_BANNER_WIDTH = 1200


def _check_image(image, *, min_width=0, min_height=0):
    if image.size > MAX_IMAGE_SIZE:
        raise forms.ValidationError(f"The image must be under {MAX_IMAGE_SIZE // (1024 * 1024)} MB.")
    if image.image.format not in ("JPEG", "PNG", "WEBP"):
        raise forms.ValidationError("Use a JPG, PNG or WEBP image.")
    width, height = image.image.size
    if width < min_width or height < min_height:
        raise forms.ValidationError(f"The image must be at least {min_width}×{min_height or 'any'} pixels (yours is {width}×{height}).")
    return image


def _clean_name(name, exclude_pk=None):
    name = " ".join(name.split())
    if len(name) < 3:
        raise forms.ValidationError("Use at least 3 characters.")
    if not slugify(name):
        raise forms.ValidationError("Use some letters or numbers in the name.")
    taken = Organization.objects.filter(name__iexact=name)
    if exclude_pk:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise forms.ValidationError("There's already an organization with that name.")
    return name


class CreateOrganizationForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "e.g. Savannah Studio", "autocomplete": "off"}))
    tagline = forms.CharField(max_length=160, required=False, widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "One line about what you make (optional)"}))

    def clean_name(self):
        return _clean_name(self.cleaned_data["name"])


class OrganizationPageForm(forms.ModelForm):
    """The organization's page: name, tagline, bio, pictures and links."""

    logo_upload = forms.ImageField(required=False, label="Profile picture")
    banner_upload = forms.ImageField(required=False, label="Banner")
    remove_logo = forms.BooleanField(required=False)
    remove_banner = forms.BooleanField(required=False)
    links = JSONRowsField(row_cleaner=clean_link_row, required=False, max_rows=12, label="Links")

    class Meta:
        model = Organization
        fields = ["name", "tagline", "description", "accepts_requests"]
        labels = {"description": "Biography", "accepts_requests": "Let members ask to join from the organization's page"}
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "autocomplete": "off"}),
            "tagline": forms.TextInput(attrs={"class": INPUT, "placeholder": "One line about what you make"}),
            "description": forms.Textarea(attrs={"class": "zb-textarea text-sm resize-y w-full", "rows": 10, "placeholder": "Who you are, what you make, how to get involved. Markdown works."}),
        }

    def clean_name(self):
        return _clean_name(self.cleaned_data["name"], exclude_pk=self.instance.pk)

    def clean_logo_upload(self):
        image = self.cleaned_data.get("logo_upload")
        return _check_image(image, min_width=MIN_LOGO_SIZE, min_height=MIN_LOGO_SIZE) if image else None

    def clean_banner_upload(self):
        image = self.cleaned_data.get("banner_upload")
        return _check_image(image, min_width=MIN_BANNER_WIDTH) if image else None

    def links_widget(self):
        if self.is_bound:
            rows = raw_rows(self.data, self.add_prefix("links"))
        else:
            rows = [{"kind": link.kind, "url": link.url, "label": link.label} for link in self.instance.links.all()]
        return widget_config(
            name=self.add_prefix("links"),
            rows=rows,
            blank={"kind": DEFAULT_LINK_PRESET, "url": "", "label": ""},
            addLabel="Add link",
            emptyText="No links.",
            presets=LINK_PRESETS,
            sortable=True,
        )

    @transaction.atomic
    def save(self, commit=True):
        org = super().save(commit=False)
        for field, upload, remove in (("logo", "logo_upload", "remove_logo"), ("banner", "banner_upload", "remove_banner")):
            current = getattr(org, field)
            if self.cleaned_data.get(upload):
                if current:
                    current.delete(save=False)
                setattr(org, field, self.cleaned_data[upload])
            elif self.cleaned_data.get(remove) and current:
                current.delete(save=False)
                setattr(org, field, None)
        org.save()
        org.links.all().delete()
        for order, row in enumerate(self.cleaned_data.get("links") or []):
            OrganizationLink.objects.create(organization=org, order=order, **row)
        return org


class InviteForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "Username", "autocomplete": "off"}))

    def clean_username(self):
        name = self.cleaned_data["username"].strip().lstrip("@")
        member = get_user_model().objects.filter(username__iexact=name, is_active=True).first()
        if member is None:
            raise forms.ValidationError("There's no member with that username.")
        return member


class MemberSettingsForm(forms.Form):
    """One member's title and permissions, set by the owner or a co-owner."""

    title = forms.CharField(max_length=80, required=False, widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "e.g. Texture artist"}))
    can_publish = forms.BooleanField(required=False)
    can_use_inbox = forms.BooleanField(required=False)
    can_edit_profile = forms.BooleanField(required=False)


class DeleteOrganizationForm(forms.Form):
    confirm = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": INPUT, "autocomplete": "off"}))

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization

    def clean_confirm(self):
        if self.cleaned_data["confirm"].strip() != self.organization.name:
            raise forms.ValidationError("Type the name exactly as it's shown.")
        return self.cleaned_data["confirm"]
