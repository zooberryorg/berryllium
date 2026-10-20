import re
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render
from django.utils import timezone

from berryllium.mods.models import Mod, ModImage
from berryllium.mods.review import _labels
from berryllium.mods.settings import GAME_OPTIONS, MOD_CATEGORIES, MOD_CATEGORY_ICONS
from berryllium.shared.models import Tag

PAGE_SIZE = 24
MAX_QUERY_LENGTH = 100
MAX_TAGS = 10

SORTS = {
    "recent": ("Newest", ["-publish_date"]),
    "updated": ("Recently updated", ["-last_updated"]),
    "downloads": ("Most downloaded", ["-download_count", "-publish_date"]),
    "likes": ("Most liked", ["-like_count", "-publish_date"]),
    "title": ("Title (A–Z)", ["title"]),
}
DEFAULT_SORT = "recent"

PERIODS = {
    "today": ("Today", 1),
    "week": ("This week", 7),
    "month": ("This month", 30),
    "year": ("This year", 365),
}


def published_mods():
    """Mods anyone can see: not drafts, and their publish date has arrived."""
    return Mod.objects.filter(draft=False, publish_date__lte=timezone.now())

def _csv_has(field, key):
    """Match one key in a comma-separated field like category="animals, scripts"."""
    return Q(**{f"{field}__regex": rf"(^|,\s*){re.escape(key)}(\s*,|$)"})
