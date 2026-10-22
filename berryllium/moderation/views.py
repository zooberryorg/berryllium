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

# --------------------------------------------------------------------------- overview


@moderator_required
def overview(request):
    mods = Mod.objects.all()
    stats = [
        {"label": "Files waiting", "value": ModFile.objects.filter(status=ModFile.Status.PENDING).count(),
         "url": reverse("moderation_files"), "icon": "bi-inboxes", "attention": True},
        {"label": "Published mods", "value": mods.filter(status_filter("published")).count(),
         "url": reverse("moderation_mods") + "?status=published", "icon": "bi-puzzle"},
        {"label": "Scheduled", "value": mods.filter(status_filter("scheduled")).count(),
         "url": reverse("moderation_mods") + "?status=scheduled", "icon": "bi-calendar-event"},
        {"label": "Drafts", "value": mods.filter(status_filter("draft")).count(),
         "url": reverse("moderation_mods") + "?status=draft", "icon": "bi-pencil"},
        {"label": "Members", "value": Member.objects.filter(is_active=True).count(), "url": "", "icon": "bi-people"},
        {"label": "Tags", "value": Tag.objects.count(), "url": reverse("moderation_tags"), "icon": "bi-tags"},
    ]
    context = {
        "stats": stats,
        "waiting_files": ModFile.objects.filter(status=ModFile.Status.PENDING)
            .select_related("filegroup__mod__uploaded_by").order_by("uploaded_at")[:5],
        "recent_mods": mods.filter(status_filter("published")).select_related("uploaded_by").order_by("-publish_date")[:6],
        "panel_nav": _nav(request, "moderation_overview"),
    }
    return render(request, "moderation/overview.html", context)


# --------------------------------------------------------------------------- file queue


@moderator_required
def files(request):
    status = request.GET.get("status", "pending")
    status = status if status in dict(FILE_STATUSES) else "pending"
    queryset = ModFile.objects.select_related("filegroup__mod__uploaded_by")
    tabs = [
        {"key": key, "label": label, "active": key == status,
         "count": queryset.filter(status=key).count() if key else queryset.count(),
         "url": f"?status={key}" if key else "?status="}
        for key, label in FILE_STATUSES
    ]
    if status:
        queryset = queryset.filter(status=status)
    # oldest first while waiting (a queue); newest first otherwise
    queryset = queryset.order_by("uploaded_at" if status == "pending" else "-uploaded_at")
    page = Paginator(queryset, 30).get_page(request.GET.get("page"))
    return render(request, "moderation/files.html", {
        "status": status, "status_tabs": tabs, "page": page,
        "next_url": request.get_full_path(),
        "panel_nav": _nav(request, "moderation_files"),
    })

@moderator_required
@require_POST
def files_review(request):
    """Approve or reject one or more files. Rejected files are hidden from downloads on the mod page."""
    action = request.POST.get("action")
    ids = [int(value) for value in request.POST.getlist("ids") if value.isdigit()]
    note = request.POST.get("note", "").strip()[:1000]
    new_status = {"approve": ModFile.Status.APPROVED, "reject": ModFile.Status.FAILED}.get(action)
    if not new_status or not ids:
        messages.warning(request, "Select at least one file and choose Approve or Reject.")
    elif action == "reject" and not note:
        messages.error(request, "Add a note saying why the file was rejected. The uploader will need it.")
    else:
        count = ModFile.objects.filter(pk__in=ids).update(
            status=new_status, moderated_at=timezone.now(), moderation_notes=note
        )
        verb = "Approved" if action == "approve" else "Rejected"
        messages.success(request, f"{verb} {count} file{'s' if count != 1 else ''}.")
    next_url = request.POST.get("next", "")
    return redirect(next_url if next_url.startswith("/moderation/") else reverse("moderation_files"))


# --------------------------------------------------------------------------- mods


@moderator_required
def mods(request):
    context = mod_list_context(request, Mod.objects.all())
    context["panel_nav"] = _nav(request, "moderation_mods")
    return render(request, "moderation/mods.html", context)


@moderator_required
@require_POST
def mods_bulk(request):
    return handle_bulk_post(request, Mod.objects.all(), reverse("moderation_mods"))