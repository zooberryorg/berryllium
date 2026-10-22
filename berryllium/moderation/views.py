from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from berryllium.mods.editing import handle_bulk_post, mod_list_context, status_filter
from berryllium.mods.models import Mod, ModFile, ModTag
from berryllium.shared.fields import proper_case
from berryllium.shared.models import Tag
from berryllium.users.models import Member
from berryllium.users.permissions import MODERATOR_GROUP, admin_required, is_site_admin, moderator_required

FILE_STATUSES = [
    ("pending", "Waiting"),
    ("approved", "Approved"),
    ("failed", "Rejected"),
    ("", "All"),
]


def _nav(request, active):
    pending = ModFile.objects.filter(status=ModFile.Status.PENDING).count()
    items = [
        ("moderation_overview", "Overview", "bi-speedometer2", None),
        ("moderation_files", "File queue", "bi-inboxes", pending),
        ("moderation_mods", "Mods", "bi-puzzle", None),
        ("moderation_tags", "Tags", "bi-tags", None),
    ]
    nav = [{"url": reverse(name), "label": label, "icon": icon, "count": count, "active": name == active}
           for name, label, icon, count in items]
    if is_site_admin(request.user):
        nav.append({"group": "Admins"})
        nav.append({"url": reverse("moderation_team"), "label": "Team", "icon": "bi-people", "count": None,
                    "active": active == "moderation_team"})
    return nav


def _moderators_group():
    group, _ = Group.objects.get_or_create(name=MODERATOR_GROUP)
    return group

