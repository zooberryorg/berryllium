from urllib.parse import urlparse

from django.db.models import F
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from berryllium.comments.views import section_context as comments_context
from berryllium.mods.models import Mod, ModCredit, ModFile, ModFileGroup
from berryllium.users.permissions import can_edit_mod, is_moderator
from berryllium.mods.review import _labels
from berryllium.mods.settings import (
    EXPANSION_REQUIREMENTS,
    GALLERY_RATIO,
    GAME_OPTIONS,
    MOD_CATEGORIES,
    MOD_CATEGORY_ICONS,
)

TABS = ("description", "files", "credits", "comments")


def _is_public(mod):
    return not mod.draft and mod.publish_date <= timezone.now()


def _can_view(mod, user):
    """Published mods are public; drafts and scheduled mods are only viewable by the uploader and moderators."""
    if _is_public(mod):
        return True
    return user.is_authenticated and (is_moderator(user) or user.pk == mod.uploaded_by_id)


def _downloadable_files():
    """Files people can download. Everything except failed files."""
    return ModFile.objects.exclude(status=ModFile.Status.FAILED)

@require_GET
def mod_detail(request, mod_id):
    mod = get_object_or_404(Mod.objects.select_related("uploaded_by"), pk=mod_id)
    if not _can_view(mod, request.user):
        raise Http404("Mod not found.")

    # gallery is the picked thumbnail first, then the uploader's order
    images = sorted(mod.images.all(), key=lambda image: not image.is_thumbnail)
    gallery = [
        {"url": image.image.url, "title": image.title or "", "caption": image.caption or ""}
        for image in images
    ]

    groups = []
    for group in ModFileGroup.objects.filter(mod=mod):
        files = list(_downloadable_files().filter(filegroup=group))
        if files:
            groups.append({"group": group, "files": files, "size": sum(f.size or 0 for f in files)})
    all_files = [f for g in groups for f in g["files"]]

    credits = list(mod.credits.select_related("member", "author__member"))
    dependencies = list(mod.dependencies.select_related("ref"))
    now = timezone.now()
    for dep in dependencies:
        # only link to mods that visitors can open
        dep.ref_is_public = bool(dep.ref_id and not dep.is_external and not dep.ref.draft and dep.ref.publish_date <= now)

    category_keys = [key.strip() for key in (mod.category or "").split(",") if key.strip()]
    context = {
        "mod": mod,
        "is_public": _is_public(mod),
        "is_scheduled": not mod.draft and mod.publish_date > now,
        "gallery": gallery,
        "gallery_ratio": GALLERY_RATIO,
        # files
        "file_groups": groups,
        "file_count": len(all_files),
        "total_size": sum(f.size or 0 for f in all_files),
        "single_file": all_files[0] if len(all_files) == 1 else None,
        "external_host": urlparse(mod.external_url).netloc.removeprefix("www.") if mod.external_url else "",
        # people
        "collaborators": [c for c in credits if c.role == ModCredit.Role.COLLABORATOR],
        "original_authors": [c for c in credits if c.role == ModCredit.Role.ORIGINAL_AUTHOR],
        "attributions": list(mod.attributions.all()),
        # resources
        "dependencies": dependencies,
        "required_count": sum(1 for d in dependencies if d.required),
        "mod_licenses": list(mod.licenses.select_related("license")),
        "languages": list(mod.languages.all()),
        "links": list(mod.links.all()),
        "original_websites": list(mod.original_websites.all()),
        # categorization
        "categories": [
            {"key": key, "label": dict(MOD_CATEGORIES).get(key, key), "icon": MOD_CATEGORY_ICONS.get(key, "bi-folder")}
            for key in category_keys
        ],
        "game_labels": _labels(mod.game, GAME_OPTIONS),
        "expansion_labels": [label for label in _labels(mod.expansions, EXPANSION_REQUIREMENTS) if label != "None"],
        "tags": list(mod.tags.all()),
        "tabs": TABS,
        "can_edit": can_edit_mod(request.user, mod),
        "comments": comments_context(request, mod),
    }
    return render(request, "mods/detail/base.html", context)

@require_GET
def download_file(request, file_id):
    """Count download then hand over the file or send the visitor to where it's hosted."""
    file = get_object_or_404(_downloadable_files().select_related("filegroup__mod"), pk=file_id)
    mod = file.filegroup.mod
    if not _can_view(mod, request.user):
        raise Http404("File not found.")

    if _is_public(mod):
        # update() instead of save(): counting a download must not change the mod's "last updated" date
        Mod.objects.filter(pk=mod.pk).update(download_count=F("download_count") + 1)

    if file.url:
        return HttpResponseRedirect(file.url)
    if file.staged_file:
        return FileResponse(file.staged_file.open("rb"), as_attachment=True, filename=file.filename or None)
    raise Http404("This file isn't available.")
