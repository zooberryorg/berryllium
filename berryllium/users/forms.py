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

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        if Member.objects.filter(username=cleaned_data.get("username")).exists():
            self.add_error("username", "Username already exists. Use a different username.")
        
        if Member.objects.filter(email=cleaned_data.get("email")).exists():
            self.add_error("email", "Email already exists. Use a different email.")
        
        return cleaned_data


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

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password:
            try:
                member = Member.objects.get(username=username)
                if not member.check_password(password):
                    raise forms.ValidationError("Invalid username or password.")
            except Member.DoesNotExist:
                raise forms.ValidationError("Invalid username or password.")
            
        return cleaned_data