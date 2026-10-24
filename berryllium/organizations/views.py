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

