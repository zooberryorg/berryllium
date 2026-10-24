from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404, HttpResponse
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
from berryllium.users.permissions import is_moderator, is_site_admin
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
    row = services.acting_row(org, request.user)
    pending = OrganizationRequest.objects.filter(organization=org, member=request.user).first() if request.user.is_authenticated else None
    context.update({
        "org": org,
        "display_name": org.name,
        "my_row": row if not getattr(row, "as_moderator", False) else row.real_row,
        "can_manage_page": bool(row and (services.can(row, "edit_profile") or services.can(row, "manage") or services.can(row, "use_inbox"))),
        "manage_url": reverse(
            "organization_manage_page" if services.can(row, "edit_profile") else "organization_inbox", kwargs={"slug": org.slug},
        ) if row else "",
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

# --------------------------------------------------------------------------- New > Organization (modal)


@login_required
@require_http_methods(["GET", "POST"])
def create_modal(request):
    """
    The modal from the New menu. Members become the owner. Moderators and admins can also make an
    archived organization: a historical group with members but no owner.
    """
    form = CreateOrganizationForm(request.POST or None, can_archive=is_moderator(request.user))
    if request.method == "POST" and form.is_valid():
        archived = form.cleaned_data.get("archived", False)
        org = services.create_organization(request.user, form.cleaned_data["name"], form.cleaned_data["tagline"], archived=archived)
        if archived:
            messages.success(request, f"{org.name} was added as an archived organization. List its former members under Members.")
        else:
            messages.success(request, f"{org.name} is ready. Add a picture and a bio, then invite your team.")
        response = HttpResponse()
        response["HX-Redirect"] = reverse("organization_manage_page", kwargs={"slug": org.slug})
        return response
    return render(request, "organizations/create_modal.html", {"form": form})


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
    """
    (org, my membership) when the signed-in member may do permission here, otherwise 403.
    Moderators and admins get a stand-in owner row, so they can look after any organization.
    """
    org = _org(slug)
    row = services.acting_row(org, request.user)
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
        if services.can(row, permission) and not (permission == "use_inbox" and org.is_archived):
            nav.append({"url": reverse(name, kwargs={"slug": org.slug}), "label": label, "icon": icon, "count": count, "active": name == active})
    nav.append({"url": org.get_absolute_url(), "label": "View page", "icon": "bi-box-arrow-up-right", "count": None, "active": False})
    if getattr(row, "as_moderator", False):
        nav.append({"url": reverse("explore_organizations"), "label": "All organizations", "icon": "bi-arrow-left", "count": None, "active": False})
    else:
        nav.append({"url": reverse("settings_organizations"), "label": "All organizations", "icon": "bi-arrow-left", "count": None, "active": False})
    return nav

@login_required
@require_http_methods(["GET", "POST"])
def manage_page(request, slug):
    org, row = _manage(request, slug, "edit_profile")
    form = OrganizationPageForm(request.POST or None, request.FILES or None, instance=org)
    delete_form = DeleteOrganizationForm(organization=org)
    if request.method == "POST" and request.POST.get("action") == "delete":
        # the owner, or an admin (moderators can't delete organizations)
        if row.role != Role.OWNER or (getattr(row, "as_moderator", False) and not is_site_admin(request.user)):
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
        "can_delete": row.role == Role.OWNER and (not getattr(row, "as_moderator", False) or is_site_admin(request.user)),
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
                if org.is_archived:
                    # no invitation to accept: former members are listed directly
                    _, problem = services.add_to_archived(org, member, request.user)
                    if problem:
                        messages.warning(request, problem)
                    else:
                        messages.success(request, f"Listed {member.username} as a member.")
                    return redirect("organization_manage_members", slug=org.slug)
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
            elif getattr(row, "as_moderator", False):
                messages.success(request, f"{target.user.username} is now the owner of {org.name}.")
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
        "as_moderator": getattr(row, "as_moderator", False),
        # the owner hands over ownership; an admin can give any organization an owner (an archived one becomes managed)
        "can_transfer": row.role == Role.OWNER and (not getattr(row, "as_moderator", False) or is_site_admin(request.user)),
        "invite_form": invite_form,
        "join_requests": org.requests.filter(kind=OrganizationRequest.Kind.REQUEST).select_related("member"),
        "invites": org.requests.filter(kind=OrganizationRequest.Kind.INVITE).select_related("member", "created_by"),
    })

# --------------------------------------------------------------------------- the organization's inbox

@login_required
@require_GET
def org_inbox(request, slug):
    org, row = _manage(request, slug, "use_inbox")
    page = Paginator(inbox.org_conversation_list(org), 25).get_page(request.GET.get("page"))
    return render(request, "organizations/manage/inbox.html", {
        "panel_nav": _org_nav(request, org, row, "organization_inbox"),
        "org": org, "my_row": row, "conversations": page,
    })

@require_GET
def org_conversation_updates(request, slug, conversation_id):
    """New messages for the poller in an open organization conversation."""
    from berryllium.inbox.views import updates_response
    if not request.user.is_authenticated:
        return HttpResponse(status=286)  # stop polling
    org = _org(slug)
    side = inbox.org_side(conversation_id, org) if services.can(services.acting_row(org, request.user), "use_inbox") else None
    if side is None:
        return HttpResponse(status=286)
    url = reverse("organization_conversation_updates", kwargs={"slug": org.slug, "conversation_id": conversation_id})
    return updates_response(request, side, url)

@login_required
@require_http_methods(["GET", "POST"])
def org_conversation(request, slug, conversation_id):
    org, row = _manage(request, slug, "use_inbox")
    side = inbox.org_side(conversation_id, org)
    if side is None:
        raise Http404("Conversation not found.")
    convo = side.conversation
    other = next((s.member for s in convo.memberships.select_related("member") if s.member_id), None)
    quote = None
    quote_id = request.POST.get("quote") or request.GET.get("quote")
    if quote_id and str(quote_id).isdigit():
        quote = Message.objects.select_related("sender").filter(pk=int(quote_id), conversation=convo).first()
    if request.method == "POST" and request.POST.get("action") == "delete":
        inbox.clear(side)
        messages.success(request, f"Conversation deleted for {org.name}. {other.username if other else 'The member'} keeps their copy.")
        return redirect("organization_inbox", slug=org.slug)
    form = MessageForm(request.POST or None, auto_id="id_reply_%s", rows=5)
    problem = ""
    if request.method == "POST" and form.is_valid():
        problem = inbox.problem_sending(request.user, other, as_org=org)
        if not problem and inbox.too_soon(request.user):
            problem = "You're sending messages very quickly. Wait a moment and try again."
        if not problem:
            message = inbox.send_message(convo, request.user, other, form.cleaned_data["body"], quote=quote, as_org=org)
            url = reverse("organization_conversation", kwargs={"slug": org.slug, "conversation_id": convo.pk})
            return redirect(f"{url}#message-{message.pk}")
    shown, has_earlier = inbox.visible_messages(side, show_all=bool(request.GET.get("all")))
    first_unread = None
    if side.last_read_at:
        first_unread = next((m.pk for m in shown if m.created_at > side.last_read_at and m.sent_as_id is None), None)
    inbox.mark_read(side)
    page = Paginator(inbox.org_conversation_list(org), 25).get_page(request.GET.get("page"))
    return render(request, "organizations/manage/conversation.html", {
        "panel_nav": _org_nav(request, org, row, "organization_inbox"),
        "org": org, "my_row": row, "conversations": page, "membership": side,
        "conversation": convo, "other": other, "thread": shown, "has_earlier": has_earlier,
        "first_unread": first_unread, "form": form, "quote": quote,
        "last_id": shown[-1].pk if shown else 0,
        "poll_url": reverse("organization_conversation_updates", kwargs={"slug": org.slug, "conversation_id": convo.pk}),
        "problem": problem or (inbox.problem_sending(request.user, other, as_org=org) if request.method == "GET" else ""),
    })