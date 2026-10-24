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

# --------------------------------------------------------------------------- managing one organization

def _manage(request, slug, permission):
    """(org, my membership) when the signed-in member may do `permission` here, otherwise 403."""
    org = _org(slug)
    row = services.membership(org, request.user)
    if not services.can(row, permission):
        raise PermissionDenied
    return org, row

def _org_nav(request, org, row, active):
    nav = [{"group": org.name}]
    items = [
        ("organization_manage_page", "Page", "bi-card-text", "edit_profile", None),
        ("organization_manage_members", "Members", "bi-people", "manage", org.memberships.count()),
        ("organization_inbox", "Inbox", "bi-envelope", "use_inbox", (inbox.org_unread_count(org) or None) if row.has("use_inbox") else None),
    ]
    for name, label, icon, permission, count in items:
        if services.can(row, permission):
            nav.append({"url": reverse(name, kwargs={"slug": org.slug}), "label": label, "icon": icon, "count": count, "active": name == active})
    nav.append({"url": org.get_absolute_url(), "label": "View page", "icon": "bi-box-arrow-up-right", "count": None, "active": False})
    nav.append({"url": reverse("settings_organizations"), "label": "All organizations", "icon": "bi-arrow-left", "count": None, "active": False})
    return nav

@login_required
@require_http_methods(["GET", "POST"])
def manage_page(request, slug):
    org, row = _manage(request, slug, "edit_profile")
    form = OrganizationPageForm(request.POST or None, request.FILES or None, instance=org)
    delete_form = DeleteOrganizationForm(organization=org)
    if request.method == "POST" and request.POST.get("action") == "delete":
        if row.role != Role.OWNER:
            raise PermissionDenied
        delete_form = DeleteOrganizationForm(request.POST, organization=org)
        if delete_form.is_valid():
            name = org.name
            org.delete()
            messages.success(request, f"{name} was deleted. Its mods stay up, credited to their uploaders.")
            return redirect("settings_organizations")
        form = OrganizationPageForm(instance=org)
    elif request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Saved.")
        return redirect("organization_manage_page", slug=org.slug)
    return render(request, "organizations/manage/page.html", {
        "panel_nav": _org_nav(request, org, row, "organization_manage_page"),
        "org": org, "my_row": row, "form": form, "delete_form": delete_form,
    })

@login_required
@require_http_methods(["GET", "POST"])
def manage_members(request, slug):
    org, row = _manage(request, slug, "manage")
    invite_form = InviteForm(request.POST if request.POST.get("action") == "invite" else None)
    if request.method == "POST":
        action = request.POST.get("action")
        target = None
        if request.POST.get("member", "").isdigit():
            target = org.memberships.select_related("user").filter(pk=int(request.POST["member"])).first()
        if action == "invite":
            if invite_form.is_valid():
                member = invite_form.cleaned_data["username"]
                _, problem = services.invite(org, member, request.user)
                if problem:
                    messages.warning(request, problem)
                elif services.membership(org, member):
                    messages.success(request, f"{member.username} had asked to join, so they're in now.")
                else:
                    messages.success(request, f"Invited {member.username}.")
                return redirect("organization_manage_members", slug=org.slug)
        elif action in ("approve", "decline_request", "cancel_invite") and request.POST.get("request", "").isdigit():
            pending = org.requests.select_related("member").filter(pk=int(request.POST["request"])).first()
            if pending is not None:
                if action == "approve" and pending.kind == OrganizationRequest.Kind.REQUEST:
                    services.accept(pending, request.user)
                    messages.success(request, f"{pending.member.username} is now a member.")
                else:
                    services.decline(pending)
                    messages.success(request, "Done.")
            return redirect("organization_manage_members", slug=org.slug)
        elif target is not None and action == "update":
            if not services.can_change(row, target):
                raise PermissionDenied
            form = MemberSettingsForm(request.POST)
            if form.is_valid():
                for field in ("title", "can_publish", "can_use_inbox", "can_edit_profile"):
                    setattr(target, field, form.cleaned_data[field])
                target.save(update_fields=["title", "can_publish", "can_use_inbox", "can_edit_profile"])
                messages.success(request, f"Saved {target.user.username}'s settings.")
            return redirect("organization_manage_members", slug=org.slug)
        elif target is not None and action == "remove":
            if not services.can_change(row, target):
                raise PermissionDenied
            name = target.user.username
            target.delete()
            messages.success(request, f"Removed {name}.")
            return redirect("organization_manage_members", slug=org.slug)
        elif target is not None and action in ("make_co_owner", "make_member"):
            problem = services.set_role(row, target, Role.CO_OWNER if action == "make_co_owner" else Role.MEMBER)
            if problem:
                messages.warning(request, problem)
            else:
                messages.success(request, f"{target.user.username} is now a {target.get_role_display().lower()}.")
            return redirect("organization_manage_members", slug=org.slug)
        elif target is not None and action == "transfer":
            problem = services.transfer_ownership(row, target)
            if problem:
                messages.warning(request, problem)
            else:
                messages.success(request, f"{target.user.username} is now the owner. You're a co-owner.")
            return redirect("organization_manage_members", slug=org.slug)
    rows = _member_rows(org)
    for member_row in rows:
        member_row.editable = services.can_change(row, member_row)
    return render(request, "organizations/manage/members.html", {
        "panel_nav": _org_nav(request, org, row, "organization_manage_members"),
        "org": org, "my_row": row, "rows": rows,
        "permissions": services.PERMISSIONS,
        "invite_form": invite_form,
        "join_requests": org.requests.filter(kind=OrganizationRequest.Kind.REQUEST).select_related("member"),
        "invites": org.requests.filter(kind=OrganizationRequest.Kind.INVITE).select_related("member", "created_by"),
    })