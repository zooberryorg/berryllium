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