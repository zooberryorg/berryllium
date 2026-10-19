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

def person_item(kind, obj, locked=False):
    """Pill/search-result dict for a member, an author or a new name."""
    if kind == "member":
        return {
            "value": f"m:{obj.pk}",
            "label": obj.username,
            "sublabel": "You (uploader)" if locked else obj.get_full_name(),
            "locked": locked,
        }
    if kind == "author":
        return {"value": f"a:{obj.pk}", "label": obj.name, "sublabel": "Not a member"}
    return {"value": f"{NEW_PREFIX}{obj}", "label": obj, "sublabel": NEW_PERSON_SUBLABEL, "isNew": True}

def resolve_people(values, strict=True):
    """
    ["m:3", "a:7", "new:Jane"] -> [("member", Member), ("author", Author), ("new", "Jane")], in order.
    """
    User = get_user_model()
    member_ids = [int(v[2:]) for v in values if v.startswith("m:") and v[2:].isdigit()]
    author_ids = [int(v[2:]) for v in values if v.startswith("a:") and v[2:].isdigit()]
    members = User.objects.filter(is_active=True).in_bulk(member_ids)
    authors = Author.objects.in_bulk(author_ids)

    resolved = []
    for value in values:
        if value.startswith("m:") and value[2:].isdigit() and int(value[2:]) in members:
            resolved.append(("member", members[int(value[2:])]))
        elif value.startswith("a:") and value[2:].isdigit() and int(value[2:]) in authors:
            resolved.append(("author", authors[int(value[2:])]))
        elif value.startswith(NEW_PREFIX):
            name = " ".join(value[len(NEW_PREFIX):].split())[:MAX_NAME_LENGTH]
            resolved.append(("new", name))
        elif strict:
            raise ValidationError("One of the selected people no longer exists. Remove it and try again.")
    return resolved

def people_items(resolved, uploader=None):
    """Pills for resolved people; the uploader (if given) comes first and is locked."""
    items = []
    if uploader is not None:
        items.append(person_item("member", uploader, locked=True))
    for kind, obj in resolved:
        if kind == "member" and uploader is not None and obj.pk == uploader.pk:
            continue
        items.append(person_item(kind, obj))
    return items

def credits_as_resolved(mod, role):
    resolved = []
    for credit in mod.credits.filter(role=role).select_related("member", "author"):
        if credit.member_id:
            resolved.append(("member", credit.member))
        elif credit.author_id:
            resolved.append(("author", credit.author))
        elif credit.pending_name:
            resolved.append(("new", credit.pending_name))
    return resolved

def save_credits(mod, role, resolved, uploader=None):
    """Replace this mod's credits for `role`. The uploader (if given) is always first."""
    with transaction.atomic():
        mod.credits.filter(role=role).delete()
        order = 0
        if uploader is not None:
            ModCredit.objects.create(mod=mod, role=role, member=uploader, order=order)
            order += 1
        for kind, obj in resolved:
            if kind == "member" and uploader is not None and obj.pk == uploader.pk:
                continue
            ModCredit.objects.create(
                mod=mod,
                role=role,
                member=obj if kind == "member" else None,
                author=obj if kind == "author" else None,
                pending_name=obj if kind == "new" else "",
                order=order,
            )
            order += 1

def website_item(website):
    details = [part for part in (website.years_active, "Offline" if website.is_offline else "") if part]
    return {"value": str(website.pk), "label": website.name, "sublabel": " · ".join(details)}


def website_items_from_values(values):
    ids = [int(v) for v in values if str(v).isdigit()]
    websites = ArchivedWebsite.objects.in_bulk(ids)
    return [website_item(websites[i]) for i in ids if i in websites]
