from django import forms

from berryllium.comments.services import MAX_LENGTH


class CommentForm(forms.Form):
    body = forms.CharField(
        max_length=MAX_LENGTH,
        label="Comment",
        widget=forms.Textarea(attrs={
            "class": "zb-textarea text-sm resize-y w-full",
            "rows": 5,
            "placeholder": "Write a comment. Markdown works, and the toolbar helps.",
        }),
        error_messages={"required": "Write something first.", "max_length": f"Keep it under {MAX_LENGTH:,} characters."},
    )

    def __init__(self, *args, placeholder=None, rows=None, **kwargs):
        super().__init__(*args, **kwargs)
        attrs = self.fields["body"].widget.attrs
        if placeholder:
            attrs["placeholder"] = placeholder
        if rows:
            attrs["rows"] = rows

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Write something first.")
        return body
