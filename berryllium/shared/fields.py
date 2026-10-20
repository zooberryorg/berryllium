# fields that are shared across the site

import json

from django import forms
from django.core.exceptions import ValidationError

_url_field = forms.URLField(assume_scheme="https", max_length=500)


def clean_text(value, max_length, *, required=False, label="This field", multiline=False):
    """Cleans text input by trimming whitespace, collapsing spaces for single-line fields and validating length constraints"""
    value = str(value or "").strip()
    if not multiline:
        value = " ".join(value.split())
    if required and not value:
        raise ValidationError(f"{label} is required.")
    if len(value) > max_length:
        raise ValidationError(f"{label} can be at most {max_length} characters.")
    return value


def clean_url(value, *, required=True, label="URL"):
    value = str(value or "").strip()
    if not value:
        if required:
            raise ValidationError(f"{label} is required.")
        return ""
    try:
        return _url_field.clean(value)
    except ValidationError:
        raise ValidationError(f"{label} isn't a valid web address.")
