from django import forms
from django.contrib.auth import get_user_model

from berryllium.comments.forms import CommentForm
from berryllium.inbox.models import InboxQuota, InboxSettings


class MessageForm(CommentForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("placeholder", "Write a message. Markdown works, and the toolbar helps.")
        super().__init__(*args, **kwargs)
        self.fields["body"].label = "Message"


class NewMessageForm(MessageForm):
    to = forms.CharField(
        max_length=150,
        label="To",
        widget=forms.TextInput(attrs={"class": "zb-input text-sm w-full", "placeholder": "Username", "autocomplete": "off"}),
    )

    field_order = ["to", "body"]

    def clean_to(self):
        name = self.cleaned_data["to"].strip().lstrip("@")
        member = get_user_model().objects.filter(username__iexact=name, is_active=True).first()
        if member is None:
            raise forms.ValidationError("There's no member with that username.")
        return member


class DefaultLimitForm(forms.ModelForm):
    class Meta:
        model = InboxSettings
        fields = ["default_limit"]
        widgets = {"default_limit": forms.NumberInput(attrs={"class": "zb-input text-sm w-32", "min": 0, "max": 100000})}

    def clean_default_limit(self):
        value = self.cleaned_data["default_limit"]
        if value > 100000:
            raise forms.ValidationError("Keep it at 100,000 or less.")
        return value


class QuotaForm(forms.Form):
    """Give one member a different inbox size."""

    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "zb-input text-sm w-full", "placeholder": "Username", "autocomplete": "off"}))
    limit = forms.IntegerField(min_value=0, max_value=100000, widget=forms.NumberInput(attrs={"class": "zb-input text-sm w-full", "placeholder": "Messages"}))
    note = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={"class": "zb-input text-sm w-full", "placeholder": "Why (only moderators see this)"}))

    def clean_username(self):
        name = self.cleaned_data["username"].strip().lstrip("@")
        member = get_user_model().objects.filter(username__iexact=name).first()
        if member is None:
            raise forms.ValidationError("There's no member with that username.")
        return member

    def save(self, by):
        quota, _ = InboxQuota.objects.update_or_create(
            member=self.cleaned_data["username"],
            defaults={"limit": self.cleaned_data["limit"], "note": self.cleaned_data["note"], "set_by": by},
        )
        return quota
