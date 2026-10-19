"""
Backend for the search picker fields used in several fields.

Each pill is submitted as one hidden input, so a picker field receives a list of
string values:

    people (collaborators / original authors)
        "m:<member id>"    a site member
        "a:<author id>"    an existing Author without an account
        "new:<name>"       a new author, created only when the mod is published
    websites               "<ArchivedWebsite id>"
    tags                   "<Tag id>" or "new:<name>" (new tag, created on publish)
"""

import json

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from berryllium.mods.models import ModCredit, ModTag
from berryllium.shared.models import ArchivedWebsite, Tag
from berryllium.users.models import Author

NEW_PREFIX = "new:"
MAX_NAME_LENGTH = 150
MAX_TAG_LENGTH = 50
NEW_PERSON_SUBLABEL = "New author, added when the mod is published"
NEW_TAG_SUBLABEL = "New tag, added when the mod is published"

class PickerField(forms.Field):
    """Multi-value field filled by the search picker (one hidden input per pill)."""

    widget = forms.MultipleHiddenInput

    def __init__(self, *, allow_new=False, max_items=50, **kwargs):
        self.allow_new = allow_new
        self.max_items = max_items
        super().__init__(**kwargs)

    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, str):
            value = [value]
        seen, cleaned = set(), []
        for item in value:
            item = str(item).strip()
            if item and item.lower() not in seen:
                seen.add(item.lower())
                cleaned.append(item)
        return cleaned

    def validate(self, value):
        super().validate(value)
        if len(value) > self.max_items:
            raise ValidationError(f"You can add at most {self.max_items}.")
        for item in value:
            if item.startswith(NEW_PREFIX):
                if not self.allow_new:
                    raise ValidationError("New entries can't be created here.")
                name = item[len(NEW_PREFIX):].strip()
                if not name:
                    raise ValidationError("New entries need a name.")


def picker_config(*, name, search_url, items, title, placeholder, allow_new=False, empty_text=""):
    """JSON handed to searchPicker() in the template."""
    return json.dumps(
        {
            "name": name,
            "searchUrl": search_url,
            "items": items,
            "title": title,
            "placeholder": placeholder,
            "allowCreate": allow_new,
            "emptyText": empty_text,
        }
    )
