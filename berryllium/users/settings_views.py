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
        ("settings_posts", "My posts", "bi-journal-text", request.user.posts.count()),
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

@login_required
def settings_preferences(request):
    form = PreferencesForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Preferences saved. Dates and times across the site now use your formats.")
        return redirect("settings_preferences")
    return render(request, "users/settings/preferences.html", {"form": form, "panel_nav": _nav(request, "settings_preferences")})

@login_required
def settings_account(request):
    email_form = EmailForm(instance=request.user)
    password_form = StyledPasswordChangeForm(request.user)
    if request.method == "POST" and "save_email" in request.POST:
        email_form = EmailForm(request.POST, instance=request.user)
        if email_form.is_valid():
            email_form.save()
            messages.success(request, "Email address updated.")
            return redirect("settings_account")
    elif request.method == "POST" and "save_password" in request.POST:
        password_form = StyledPasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # stay signed in on this device
            messages.success(request, "Password changed.")
            return redirect("settings_account")
    return render(request, "users/settings/account.html", {
        "email_form": email_form,
        "password_form": password_form,
        "panel_nav": _nav(request, "settings_account"),
    })

@login_required
def settings_mods(request):
    context = mod_list_context(request, _my_mods(request.user))
    context["panel_nav"] = _nav(request, "settings_mods")
    return render(request, "users/settings/mods.html", context)


@login_required
@require_POST
def settings_mods_bulk(request):
    return handle_bulk_post(request, _my_mods(request.user), reverse("settings_mods"))