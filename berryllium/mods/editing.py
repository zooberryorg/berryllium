from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from berryllium.mods.models import ModDescriptionImage, ModFile, ModImage
from berryllium.mods.pickers import publish_mod
from berryllium.mods.review import review_issues


def open_for_editing(request, mod):
    draft_ids = request.session.get("draft_ids", [])
    if mod.pk not in draft_ids:
        draft_ids.append(mod.pk)
    request.session["draft_ids"] = draft_ids
    request.session["session_id"] = mod.pk


def close_editing(request, mod_id):
    request.session["draft_ids"] = [i for i in request.session.get("draft_ids", []) if i != mod_id]
    if request.session.get("session_id") == mod_id:
        request.session.pop("session_id")


def unpublish(mod):
    """Move a mod back to drafts. Its publish date is kept, so republishing doesn't make it "new"."""
    if not mod.draft:
        mod.draft = True
        mod.save(update_fields=["draft"])


def try_publish(mod):
    """Publish a draft if nothing blocks it. Returns the list of problems (empty when published)."""
    problems, _ = review_issues(mod)
    if problems:
        return problems
    publish_mod(mod)
    return []


def delete_mod(mod):
    """Delete a mod and the files it stored (uploads, screenshots, description images)."""
    stored = [f.staged_file for f in ModFile.objects.filter(filegroup__mod=mod) if f.staged_file]
    stored += [image.image for image in ModImage.objects.filter(mod=mod) if image.image]
    # description images remove their own files when deleted (see models.py)
    with transaction.atomic():
        ModDescriptionImage.objects.filter(mod=mod).delete()
        mod.delete()
    for field_file in stored:
        try:
            field_file.storage.delete(field_file.name)
        except OSError:
            pass  # already gone; the database rows are deleted either way


# --------------------------------------------------------------------------- lists in the panels

STATUSES = [
    ("", "All"),
    ("published", "Published"),
    ("scheduled", "Scheduled"),
    ("draft", "Drafts"),
    ("unpublished", "Unpublished"),
]
PAGE_SIZE = 25


def status_filter(status):
    """Q for one Mod.status value (see Mod.status)."""
    now = timezone.now()
    return {
        "draft": Q(draft=True, first_published_at__isnull=True),
        "unpublished": Q(draft=True, first_published_at__isnull=False),
        "scheduled": Q(draft=False, publish_date__gt=now),
        "published": Q(draft=False, publish_date__lte=now),
    }.get(status, Q())


def mod_list_context(request, mods_queryset):
    """Status tabs with counts, a title search, and one page of mods, newest edits first."""
    from berryllium.mods.views.explore import _card_image_path  # avoids a circular import

    status = request.GET.get("status", "")
    status = status if status in dict(STATUSES) else ""
    q = request.GET.get("q", "").strip()[:100]

    tabs = []
    for key, label in STATUSES:
        params = request.GET.copy()
        params.pop("page", None)
        params["status"] = key
        if not key:
            params.pop("status")
        tabs.append({
            "key": key, "label": label, "active": key == status,
            "count": mods_queryset.filter(status_filter(key)).count(),
            "url": f"?{params.urlencode()}",
        })

    results = mods_queryset.filter(status_filter(status))
    if q:
        results = results.filter(title__icontains=q)
    results = results.select_related("uploaded_by").annotate(card_image_path=_card_image_path()).order_by("-last_updated")
    page = Paginator(results, PAGE_SIZE).get_page(request.GET.get("page"))
    for mod in page.object_list:
        mod.card_image_url = default_storage.url(mod.card_image_path) if mod.card_image_path else None

    page_query = request.GET.copy()
    page_query.pop("page", None)
    return {
        "status_tabs": tabs,
        "status": status,
        "q": q,
        "page": page,
        "page_range": list(page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)),
        "page_query": page_query.urlencode(),
        "next_url": request.get_full_path(),
    }


# --------------------------------------------------------------------------- bulk actions

BULK_ACTIONS = ("publish", "unpublish", "delete")


def _names(mods, limit=3):
    titles = [f"“{mod.title or 'Untitled mod'}”" for mod in mods[:limit]]
    extra = len(mods) - limit
    return ", ".join(titles) + (f" and {extra} more" if extra > 0 else "")


def apply_bulk_action(action, mods):
    """
    Run one bulk action on a list of mods. Returns (level, message) pairs for django.contrib.messages.
    - publish: drafts and unpublished mods that have nothing blocking them (see review_issues)
    - unpublish: published and scheduled mods go back to drafts
    - delete: permanently, with their stored files
    """
    results = []
    if action == "publish":
        done, blocked = [], []
        for mod in mods:
            if not mod.draft:
                continue
            problems = try_publish(mod)
            (blocked if problems else done).append((mod, problems))
        if done:
            results.append(("success", f"Published {_names([m for m, _ in done])}."))
        for mod, problems in blocked:
            reasons = " ".join(p["message"] for p in problems[:3])
            results.append(("warning", f"“{mod.title or 'Untitled mod'}” wasn't published: {reasons}"))
        if not done and not blocked:
            results.append(("warning", "None of the selected mods are drafts, so there was nothing to publish."))
    elif action == "unpublish":
        live = [mod for mod in mods if not mod.draft]
        for mod in live:
            unpublish(mod)
        if live:
            results.append(("success", f"Moved {_names(live)} to drafts. They're hidden until you publish them again."))
        else:
            results.append(("warning", "None of the selected mods are published."))
    elif action == "delete":
        names = _names(mods)
        for mod in mods:
            delete_mod(mod)
        results.append(("success", f"Deleted {names}."))
    return results


def handle_bulk_post(request, allowed_mods, fallback_url):
    """
    POST handler for the bulk forms. allowed_mods limits which mods this user may change
    (their own in Settings, any in Moderation); ids outside it are ignored.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.utils.http import url_has_allowed_host_and_scheme

    action = request.POST.get("action", "")
    ids = [int(value) for value in request.POST.getlist("ids") if value.isdigit()]
    mods = list(allowed_mods.filter(pk__in=ids))
    if action not in BULK_ACTIONS:
        messages.error(request, "Choose what to do with the selected mods.")
    elif not mods:
        messages.warning(request, "Select at least one mod first.")
    else:
        for level, text in apply_bulk_action(action, mods):
            getattr(messages, level)(request, text)

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = fallback_url
    return redirect(next_url)