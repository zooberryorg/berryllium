from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from berryllium.mods.editing import handle_bulk_post, mod_list_context
from berryllium.mods.models import Mod
from berryllium.users.settings_forms import EmailForm, PreferencesForm, ProfileSettingsForm, StyledPasswordChangeForm


def _my_mods(user):
    return Mod.objects.filter(uploaded_by=user)


def _nav(request, active):
    sections = [
        ("settings_profile", "Profile", "bi-person-circle", None),
        ("settings_preferences", "Preferences", "bi-sliders", None),
        ("settings_account", "Account", "bi-shield-lock", None),
        ("settings_mods", "My mods", "bi-puzzle", _my_mods(request.user).count()),
    ]
    return [
        {"url": reverse(name), "label": label, "icon": icon, "count": count, "active": name == active}
        for name, label, icon, count in sections
    ]


@login_required
def settings_home(request):
    return redirect("settings_profile")

@login_required
def settings_profile(request):
    form = ProfileSettingsForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("settings_profile")
    return render(request, "users/settings/profile.html", {"form": form, "panel_nav": _nav(request, "settings_profile")})