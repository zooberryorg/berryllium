from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from berryllium.inbox import services as inbox
from berryllium.inbox.forms import MessageForm
from berryllium.inbox.models import Message
from berryllium.mods.views.explore import published_mods
from berryllium.organizations import services
from berryllium.organizations.forms import (
    CreateOrganizationForm,
    DeleteOrganizationForm,
    InviteForm,
    MemberSettingsForm,
    OrganizationPageForm,
)
from berryllium.organizations.models import Organization, OrganizationMembership, OrganizationRequest
from berryllium.users.profiles import profile_context
Role = OrganizationMembership.Role
def _org(slug):
    return get_object_or_404(Organization, slug=slug)
def _member_rows(org):
    """Owner first, then co-owners, then members by when they joined."""
    order = {Role.OWNER: 0, Role.CO_OWNER: 1, Role.MEMBER: 2}
    rows = list(org.memberships.select_related("user"))
    return sorted(rows, key=lambda row: (order.get(row.role, 3), row.joined_at))

# --------------------------------------------------------------------------- public page
@require_GET
def profile(request, slug):
    """Org page, its mods (search, sort, pages like a member profile), members and bio."""
    org = _org(slug)
    mods = published_mods().filter(organization=org)
    context = profile_context(request, mods)
    is_htmx = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
    if is_htmx:
        return render(request, "users/profile/results.html", context)
    row = services.membership(org, request.user)
    pending = OrganizationRequest.objects.filter(organization=org, member=request.user).first() if request.user.is_authenticated else None
    context.update({
        "org": org,
        "display_name": org.name,
        "my_row": row,
        "can_manage_page": bool(row and (row.has("edit_profile") or row.is_manager or row.has("use_inbox"))),
        "pending": pending,
        "member_rows": _member_rows(org),
        "links": list(org.links.all()),
    })
    return render(request, "organizations/profile.html", context)

@login_required
@require_POST
def join(request, slug):
    org = _org(slug)
    _, problem = services.ask_to_join(org, request.user, request.POST.get("message", ""))
    if problem:
        messages.warning(request, problem)
    elif services.membership(org, request.user):
        messages.success(request, f"You're now a member of {org.name}.")
    else:
        messages.success(request, f"Asked to join {org.name}. Its owners will let you know.")
    return redirect(org.get_absolute_url())

@login_required
@require_POST
def leave(request, slug):
    org = _org(slug)
    row = services.membership(org, request.user)
    if row is None:
        return redirect(org.get_absolute_url())
    problem = services.leave(row)
    if problem:
        messages.warning(request, problem)
    else:
        messages.success(request, f"You left {org.name}.")
    return redirect("settings_organizations")

# --------------------------------------------------------------------------- Control Panel Organizations

@login_required
@require_http_methods(["GET", "POST"])
def my_organizations(request):
    from berryllium.users.settings_views import _nav  # the Control Panel menu
    form = CreateOrganizationForm(request.POST if request.POST.get("action") == "create" else None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create" and form.is_valid():
            org = services.create_organization(request.user, form.cleaned_data["name"], form.cleaned_data["tagline"])
            messages.success(request, f"{org.name} is ready. Add a picture and a bio, then invite your team.")
            return redirect("organization_manage_page", slug=org.slug)
        if action in ("accept", "decline", "cancel") and request.POST.get("request", "").isdigit():
            pending = OrganizationRequest.objects.select_related("organization").filter(pk=int(request.POST["request"]), member=request.user).first()
            if pending is not None:
                name = pending.organization.name
                if action == "accept" and pending.kind == OrganizationRequest.Kind.INVITE:
                    services.accept(pending, request.user)
                    messages.success(request, f"Welcome to {name}.")
                else:
                    services.decline(pending)
                    messages.success(request, f"Declined the invitation from {name}." if action == "decline" else f"Withdrew your request to join {name}.")
            return redirect("settings_organizations")
    rows = list(
        OrganizationMembership.objects.filter(user=request.user)
        .select_related("organization")
        .annotate(member_count=Count("organization__memberships", distinct=True))
        .order_by("organization__name")
    )
    for row in rows:
        row.unread = inbox.org_unread_count(row.organization) if row.has("use_inbox") else 0
    return render(request, "organizations/panel/list.html", {
        "panel_nav": _nav(request, "settings_organizations"),
        "rows": rows,
        "invites": OrganizationRequest.objects.filter(member=request.user, kind=OrganizationRequest.Kind.INVITE).select_related("organization", "created_by"),
        "requests": OrganizationRequest.objects.filter(member=request.user, kind=OrganizationRequest.Kind.REQUEST).select_related("organization"),
        "form": form,
    })