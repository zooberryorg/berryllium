from django import forms
from django.forms import ModelForm, TextInput, PasswordInput

from berryllium.mods.settings import DISABLE_SUBMIT_BUTTON_ATTRS
from berryllium.users.models import Member


class MemberRegistrationForm(ModelForm):
    class Meta:
        model = Member
        fields = ["username", "email", "password"]

    username = forms.CharField(
        required=True,
        widget=TextInput(
            attrs={
                "placeholder": "Enter username...",
                "class": "zb-input text-sm",
                "autocomplete": "off",
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )

    email = forms.EmailField(
        required=True,
        widget=TextInput(
            attrs={
                "placeholder": "Enter email...",
                "class": "zb-input text-sm",
                "autocomplete": "off",
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )

    password = forms.CharField(
        required=True,
        widget=PasswordInput(
            attrs={
                "placeholder": "Enter password...",
                "class": "zb-input text-sm",
                "autocomplete": "off",
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            },
        ),
    )

    confirm_password = forms.CharField(
        required=True,
        widget=PasswordInput(
            attrs={
                "placeholder": "Confirm password...",
                "class": "zb-input text-sm",
                "autocomplete": "off",
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )


class MemberLoginForm(ModelForm):
    class Meta:
        model = Member
        fields = ["username", "password"]

    username = forms.CharField(
        required=True,
        widget=TextInput(
            attrs={
                "placeholder": "Enter username...",
                "class": "zb-input text-sm",
                "autocomplete": "off",
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )

    password = forms.CharField(
        required=True,
        widget=PasswordInput(
            attrs={
                "placeholder": "Enter password...",
                "class": "zb-input text-sm",
                "autocomplete": "off",
                **DISABLE_SUBMIT_BUTTON_ATTRS,
            }
        ),
    )