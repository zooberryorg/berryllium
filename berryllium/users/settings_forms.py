from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from berryllium.users.models import Member

INPUT = "zb-input text-sm"
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
MIN_AVATAR_SIZE = 64  # px


class ProfileSettingsForm(forms.ModelForm):
    remove_avatar = forms.BooleanField(
        required=False,
        label="Remove my picture",
        # ticking it previews the initial instead of the picture
        widget=forms.CheckboxInput(attrs={"class": "w-4 h-4 accent-gold-400", "@change": "removing = $event.target.checked"}),
    )
