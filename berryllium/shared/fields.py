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

def proper_case(value):
    """
    Makes words proper case.
    """
    raw = str(value or "").split()
    shouting = len(raw) > 1 and all(word.isupper() for word in raw)
    words = []
    for word in raw:
        if word.isupper() and len(word) <= 4 and not shouting:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)

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

class JSONRowsField(forms.Field):
    """
    A list of rows submitted as one JSON hidden input. Used by list_widgets.js.
    """

    widget = forms.HiddenInput

    def __init__(self, *, row_cleaner, max_rows=30, **kwargs):
        self.row_cleaner = row_cleaner
        self.max_rows = max_rows
        super().__init__(**kwargs)

    def to_python(self, value):
        if not value:
            return []
        try:
            data = json.loads(value)
        except (TypeError, ValueError):
            raise ValidationError("This field couldn't be read. Reload the page and try again.")
        if not isinstance(data, list):
            raise ValidationError("This field couldn't be read. Reload the page and try again.")
        return data

    def validate(self, value):
        super().validate(value)
        if len(value) > self.max_rows:
            raise ValidationError(f"You can add at most {self.max_rows}.")

    def clean(self, value):
        rows = super().clean(value)
        cleaned, errors = [], []
        for number, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append(f"Row {number}: couldn't be read.")
                continue
            try:
                cleaned.append(self.row_cleaner(row))
            except ValidationError as error:
                errors.extend(f"Row {number}: {message}" for message in error.messages)
        if errors:
            raise ValidationError(errors)
        return cleaned

def raw_rows(data, name):
    """Returns rows exactly as submitted, without cleaning or validation. Used by list_widgets.js."""
    try:
        rows = json.loads(data.get(name) or "[]")
    except (TypeError, ValueError):
        return []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
