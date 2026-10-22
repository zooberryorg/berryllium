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


    def save(self, commit=True):
        old = Member.objects.filter(pk=self.instance.pk).values_list("avatar", flat=True).first()
        member = super().save(commit=False)
        if self.cleaned_data.get("remove_avatar") and "avatar" not in self.files:
            member.avatar = None
        if commit:
            member.save()
            # delete the replaced or removed file
            if old and old != (member.avatar.name if member.avatar else ""):
                member.avatar.storage.delete(old)
        return member