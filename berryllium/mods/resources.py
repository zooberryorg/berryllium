# several helper functions for cleaning and validating mod resource data (dependencies, licenses, attributions, links)

import json

from django.core.exceptions import ValidationError
from django.db import transaction

from berryllium.mods.models import ModAttribution, ModDependency, ModLicense, ModLink
from berryllium.shared.fields import clean_text, clean_url
from berryllium.shared.links import DEFAULT_LINK_PRESET, LINK_PRESETS

MAX_CONTEXT_LENGTH = 500
MAX_VERSION_LENGTH = 100


# --------------------------------------------------------------------------- row cleaners


def clean_dependency_row(row):
    context = clean_text(row.get("context"), MAX_CONTEXT_LENGTH, label="Context", multiline=True)
    version = clean_text(row.get("version"), MAX_VERSION_LENGTH, label="Version")
    if row.get("kind") == "internal":
        mod_id = str(row.get("mod") or row.get("value") or "")
        if not mod_id.isdigit():
            raise ValidationError("Pick a mod.")
        return {"kind": "internal", "mod": int(mod_id), "context": context, "version": version}
    if row.get("kind") == "external":
        return {
            "kind": "external",
            "title": clean_text(row.get("title"), 200, required=True, label="Title"),
            "url": clean_url(row.get("url"), label="Link"),
            "context": context,
            "version": version,
        }
    raise ValidationError("Unknown dependency type.")


def clean_license_row(row):
    license_id = str(row.get("value") or "")
    if not license_id.isdigit():
        raise ValidationError("Pick a license.")
    return {
        "license": int(license_id),
        "context": clean_text(row.get("context"), 300, label="What it covers"),
    }


def clean_attribution_row(row):
    return {
        "title": clean_text(row.get("title"), 200, required=True, label="Title"),
        "url": clean_url(row.get("url"), required=False, label="Link"),
        "authors": clean_text(row.get("authors"), 300, required=True, label="Original author(s)"),
        "note": clean_text(row.get("note"), MAX_CONTEXT_LENGTH, label="Note", multiline=True),
    }


def clean_link_row(row):
    kind = row.get("kind") or DEFAULT_LINK_PRESET
    if kind not in LINK_PRESETS:
        raise ValidationError("Unknown link type.")
    return {
        "kind": kind,
        "url": clean_url(row.get("url"), label="Link"),
        "label": clean_text(row.get("label"), 100, label="Label"),
    }
