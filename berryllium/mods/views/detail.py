from urllib.parse import urlparse

from django.db.models import F
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from berryllium.mods.models import Mod, ModCredit, ModFile, ModFileGroup
from berryllium.mods.review import _labels
from berryllium.mods.settings import (
    EXPANSION_REQUIREMENTS,
    GALLERY_RATIO,
    GAME_OPTIONS,
    MOD_CATEGORIES,
    MOD_CATEGORY_ICONS,
)

TABS = ("description", "files", "credits")


def _is_public(mod):
    return not mod.draft and mod.publish_date <= timezone.now()


def _can_view(mod, user):
    """Published mods are public, drafts and scheduled mods only viewable by staff or the uploader."""
    if _is_public(mod):
        return True
    return user.is_authenticated and (user.is_staff or user.pk == mod.uploaded_by_id)


def _downloadable_files():
    """Files people can download. Everything except failed files."""
    return ModFile.objects.exclude(status=ModFile.Status.FAILED)