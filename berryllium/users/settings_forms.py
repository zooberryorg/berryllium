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

    class Meta:
        model = Member
        fields = ["avatar", "biography"]
        labels = {"avatar": "Profile picture", "biography": "About you"}
        help_texts = {
            "avatar": f"JPG, PNG or WEBP, at least {MIN_AVATAR_SIZE}×{MIN_AVATAR_SIZE}px, up to {MAX_AVATAR_SIZE // (1024 * 1024)} MB. It's shown as a circle.",
            "biography": "Shown in the About box on your profile. Up to 500 characters.",
        }
        widgets = {
            "avatar": forms.FileInput(attrs={"accept": ".jpg,.jpeg,.png,.webp", "class": "sr-only", "x-ref": "avatarInput", "@change": "preview($event)"}),
            "biography": forms.Textarea(attrs={"class": INPUT + " rounded-2xl", "rows": 5, "maxlength": 500}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        # no new file chosen: keep the current one
        if not avatar or not hasattr(avatar, "image"):
            return avatar
        if avatar.size > MAX_AVATAR_SIZE:
            raise forms.ValidationError(f"Pictures must be under {MAX_AVATAR_SIZE // (1024 * 1024)} MB.")
        if avatar.image.format not in ("JPEG", "PNG", "WEBP"):
            raise forms.ValidationError("Pictures must be JPG, PNG or WEBP.")
        width, height = avatar.image.size
        if width < MIN_AVATAR_SIZE or height < MIN_AVATAR_SIZE:
            raise forms.ValidationError(f"Pictures must be at least {MIN_AVATAR_SIZE}×{MIN_AVATAR_SIZE}px (yours is {width}×{height}).")
        return avatar

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

class PreferencesForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ["date_format", "time_format"]
        widgets = {
            "date_format": forms.RadioSelect,
            "time_format": forms.RadioSelect,
        }
        labels = {"date_format": "Dates", "time_format": "Times"}

class EmailForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ["email"]
        widgets = {"email": forms.EmailInput(attrs={"class": INPUT, "autocomplete": "email"})}
        labels = {"email": "Email address"}
        help_texts = {"email": "Used to sign in and for account messages. It isn't shown on your profile."}

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            raise forms.ValidationError("Enter an email address.")
        if Member.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT