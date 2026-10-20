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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class MemberLoginForm(forms.Form):
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



class MemberPreferencesForm(forms.ModelForm):
    """
    Display preferences for the user settings page.
    Usage: MemberPreferencesForm(request.POST or None, instance=request.user)
    """

    class Meta:
        model = Member
        fields = ["date_format", "time_format"]
        labels = {"date_format": "Date format", "time_format": "Time format"}