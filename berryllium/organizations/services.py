from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify

from berryllium.notifications.models import Notification
from berryllium.notifications.services import notify
from berryllium.organizations.models import Organization, OrganizationMembership, OrganizationRequest
from berryllium.users.permissions import is_moderator, is_site_admin

Role = OrganizationMembership.Role
PERMISSIONS = [
    ("can_publish", "Publish", "Publish mods and articles under the organization's name"),
    ("can_use_inbox", "Inbox", "Read and answer the organization's messages"),
    ("can_edit_profile", "Edit page", "Change the bio, pictures and links"),
]


# --------------------------------------------------------------------------- who may do what


def membership(org, user):
    if not (user and user.is_authenticated):
        return None
    return OrganizationMembership.objects.filter(organization=org, user=user).first()


def acting_row(org, user):
    """
    The membership to check permissions with. Moderators and admins who aren't owners get a stand-in
    owner row (not saved), so they can look after any organization, archived ones included.
    """
    row = membership(org, user)
    if is_moderator(user) and (row is None or row.role != Role.OWNER):
        stand_in = OrganizationMembership(organization=org, user=user, role=Role.OWNER)
        stand_in.as_moderator = True
        stand_in.real_row = row
        return stand_in
    return row


def can(member_row, permission):
    """permission: "manage", "publish", "use_inbox" or "edit_profile"."""
    if member_row is None:
        return False
    if permission == "use_inbox" and (member_row.organization.is_archived or getattr(member_row, "as_moderator", False)):
        # archived organizations have no inbox, and moderators don't read an organization's private messages
        return False
    if permission == "manage":
        return member_row.is_manager
    return member_row.has(permission)


def can_change(actor_row, target_row):
    """Whether user may change target's title, permissions, or remove them."""
    if actor_row is None or target_row is None or actor_row.pk == target_row.pk:
        return False
    if getattr(actor_row, "as_moderator", False):
        # moderators look after everyone but the owner (an admin can hand ownership to someone else)
        return target_row.user_id != actor_row.user_id and target_row.role != Role.OWNER
    if actor_row.role == Role.OWNER:
        return True
    return actor_row.role == Role.CO_OWNER and target_row.role == Role.MEMBER


def publishable_organizations(user):
    """Organizations this member may publish under. Moderators can also use archived ones (they archive old work)."""
    if not (user and user.is_authenticated):
        return Organization.objects.none()
    rows = OrganizationMembership.objects.filter(user=user).filter(
        Q(role__in=[Role.OWNER, Role.CO_OWNER]) | Q(can_publish=True)
    )
    allowed = Q(pk__in=rows.values("organization_id"))
    if is_moderator(user):
        allowed |= Q(is_archived=True)
    return Organization.objects.filter(allowed)


def inbox_organizations(user):
    """Organizations whose inbox this member may use."""
    if not (user and user.is_authenticated):
        return Organization.objects.none()
    rows = OrganizationMembership.objects.filter(user=user).filter(
        Q(role__in=[Role.OWNER, Role.CO_OWNER]) | Q(can_use_inbox=True)
    )
    return Organization.objects.filter(pk__in=rows.values("organization_id"))


def managers(org):
    return [row.user for row in org.memberships.filter(role__in=[Role.OWNER, Role.CO_OWNER]).select_related("user")]


def inbox_readers(org):
    rows = org.memberships.filter(Q(role__in=[Role.OWNER, Role.CO_OWNER]) | Q(can_use_inbox=True)).select_related("user")
    return [row.user for row in rows]


# --------------------------------------------------------------------------- creating


def unique_slug(name, exclude_pk=None):
    base = slugify(name)[:100] or "organization"
    slug, n = base, 2
    taken = Organization.objects.exclude(pk=exclude_pk) if exclude_pk else Organization.objects.all()
    while taken.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


@transaction.atomic
def create_organization(owner, name, tagline="", archived=False):
    """archived: a historical group (moderators and admins only). It starts without an owner or members."""
    org = Organization.objects.create(
        name=name, slug=unique_slug(name), tagline=tagline, created_by=owner,
        is_archived=archived, accepts_requests=not archived,
    )
    if not archived:
        OrganizationMembership.objects.create(organization=org, user=owner, role=Role.OWNER)
    return org


def add_to_archived(org, member, by, title=""):
    """Archived organizations list their former members directly (no invitation to accept). Returns (row, problem)."""
    if OrganizationMembership.objects.filter(organization=org, user=member).exists():
        return None, f"{member.username} is already listed."
    row = OrganizationMembership.objects.create(organization=org, user=member, role=Role.MEMBER, title=title)
    notify([member], by, Notification.Kind.ORGANIZATION, f"You were listed as a member of {org.name} (archived)", org.get_absolute_url())
    return row, ""


# --------------------------------------------------------------------------- joining


def _panel_url():
    return reverse("settings_organizations")


def _members_url(org):
    return reverse("organization_manage_members", kwargs={"slug": org.slug})


def invite(org, member, by):
    """Returns (request, problem). Inviting someone who asked to join just lets them in."""
    if OrganizationMembership.objects.filter(organization=org, user=member).exists():
        return None, f"{member.username} is already a member."
    existing = OrganizationRequest.objects.filter(organization=org, member=member).first()
    if existing is not None:
        if existing.kind == OrganizationRequest.Kind.REQUEST:
            accept(existing, by)
            return None, ""
        return existing, f"{member.username} has already been invited."
    request = OrganizationRequest.objects.create(organization=org, member=member, kind=OrganizationRequest.Kind.INVITE, created_by=by)
    notify([member], by, Notification.Kind.ORGANIZATION, f"{by.username} invited you to join {org.name}", _panel_url())
    return request, ""


def ask_to_join(org, member, message=""):
    if OrganizationMembership.objects.filter(organization=org, user=member).exists():
        return None, "You're already a member."
    existing = OrganizationRequest.objects.filter(organization=org, member=member).first()
    if existing is not None:
        if existing.kind == OrganizationRequest.Kind.INVITE:
            accept(existing, member)
            return None, ""
        return existing, "You've already asked to join."
    if org.is_archived:
        return None, f"{org.name} is an archived organization, so it isn't taking new members."
    if not org.accepts_requests:
        return None, f"{org.name} isn't taking requests to join. A co-owner can invite you."
    request = OrganizationRequest.objects.create(organization=org, member=member, kind=OrganizationRequest.Kind.REQUEST, message=message[:300], created_by=member)
    notify(managers(org), member, Notification.Kind.ORGANIZATION, f"{member.username} asked to join {org.name}", _members_url(org))
    return request, ""


@transaction.atomic
def accept(request, by):
    """Accept an invitation (by the invited member) or a request (by a manager)."""
    org, member = request.organization, request.member
    row, _ = OrganizationMembership.objects.get_or_create(organization=org, user=member, defaults={"role": Role.MEMBER})
    request.delete()
    if by.pk == member.pk:
        notify(managers(org), member, Notification.Kind.ORGANIZATION, f"{member.username} joined {org.name}", _members_url(org))
    else:
        notify([member], by, Notification.Kind.ORGANIZATION, f"You're now a member of {org.name}", org.get_absolute_url())
    return row


def decline(request):
    request.delete()


# --------------------------------------------------------------------------- roles and leaving


def set_role(actor_row, target_row, role):
    """Only the owner makes or unmakes co-owners. Returns a problem or ""."""
    if actor_row.role != Role.OWNER or target_row.pk == actor_row.pk:
        return "Only the owner can change who is a co-owner."
    if target_row.role == Role.OWNER:
        return "Hand over ownership to someone else first."
    if target_row.organization.is_archived:
        return "Archived organizations don't have co-owners."
    if role not in (Role.CO_OWNER, Role.MEMBER):
        return "Use Hand over ownership to change the owner."
    target_row.role = role
    target_row.save(update_fields=["role"])
    return ""


@transaction.atomic
def transfer_ownership(actor_row, target_row):
    """
    The owner hands over ownership (and becomes a co-owner). An admin can also give an owner to any
    organization; for an archived one that makes it a managed organization again.
    """
    org = target_row.organization
    by_admin = getattr(actor_row, "as_moderator", False) and is_site_admin(actor_row.user)
    if target_row.pk == actor_row.pk or not (actor_row.role == Role.OWNER and (not getattr(actor_row, "as_moderator", False) or by_admin)):
        return "Only the owner or an admin can hand over ownership."
    if org.is_archived and not by_admin:
        return "Only an admin can give an archived organization an owner."
    for old in org.memberships.filter(role=Role.OWNER).exclude(pk=target_row.pk):
        old.role = Role.CO_OWNER
        old.save(update_fields=["role"])
    target_row.role = Role.OWNER
    target_row.save(update_fields=["role"])
    if org.is_archived:
        org.is_archived = False
        org.save(update_fields=["is_archived"])
    notify([target_row.user], actor_row.user, Notification.Kind.ORGANIZATION,
           f"{actor_row.user.username} made you the owner of {target_row.organization.name}", _members_url(target_row.organization))
    return ""


def leave(row):
    if row.role == Role.OWNER:
        return "The owner can't leave. Hand over ownership first, or delete the organization."
    row.delete()
    return ""
