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

def _remove_url(params, key, value=None):
    """The current query string without one filter (and without the page number)."""
    query = params.copy()
    query.pop("page", None)
    if value is None:
        query.pop(key, None)
    else:
        query.setlist(key, [v for v in query.getlist(key) if v != value])
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"

def _read_filters(params):
    categories, games = dict(MOD_CATEGORIES), dict(GAME_OPTIONS)
    category = params.get("category", "")
    game = params.get("game", "")
    period = params.get("period", "")
    sort = params.get("sort", "")
    return {
        "q": params.get("q", "").strip()[:MAX_QUERY_LENGTH],
        "category": category if category in categories else "",
        "game": game if game in games else "",
        "period": period if period in PERIODS else "",
        "tags": [tag for tag in params.getlist("tag") if tag][:MAX_TAGS],
        "sort": sort if sort in SORTS else DEFAULT_SORT,
    }

def _apply_filters(queryset, filters):
    if filters["q"]:
        q = filters["q"]
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(summary__icontains=q)
            | Q(uploaded_by__username__icontains=q)
            | Q(credits__member__username__icontains=q)
            | Q(credits__author__name__icontains=q)
            | Q(tags__name__icontains=q)
        ).distinct()
    if filters["category"]:
        queryset = queryset.filter(_csv_has("category", filters["category"]))
    if filters["game"]:
        queryset = queryset.filter(_csv_has("game", filters["game"]))
    if filters["period"]:
        days = PERIODS[filters["period"]][1]
        queryset = queryset.filter(publish_date__gte=timezone.now() - timedelta(days=days))
    for tag in filters["tags"]:
        queryset = queryset.filter(tags__name=tag)
    return queryset.order_by(*SORTS[filters["sort"]][1])

def _active_filters(params, filters):
    """Pills shown above the results, each with the URL that removes it."""
    active = []
    if filters["q"]:
        active.append({"label": f'"{filters["q"]}"', "name": "q", "value": "", "url": _remove_url(params, "q")})
    if filters["category"]:
        active.append({"label": dict(MOD_CATEGORIES)[filters["category"]], "name": "category", "value": "",
                       "url": _remove_url(params, "category")})
    if filters["game"]:
        active.append({"label": dict(GAME_OPTIONS)[filters["game"]], "name": "game", "value": "",
                       "url": _remove_url(params, "game")})
    if filters["period"]:
        active.append({"label": PERIODS[filters["period"]][0], "name": "period", "value": "",
                       "url": _remove_url(params, "period")})
    for tag in filters["tags"]:
        active.append({"label": f"#{tag}", "name": "tag", "value": tag, "url": _remove_url(params, "tag", tag)})
    return active

def _category_counts(base):
    return [
        {"key": key, "label": label, "icon": MOD_CATEGORY_ICONS.get(key, "bi-folder"),
         "count": base.filter(_csv_has("category", key)).count()}
        for key, label in MOD_CATEGORIES
    ]

def _popular_tags(limit=15):
    now = timezone.now()
    return (
        Tag.objects.annotate(uses=Count("mods", filter=Q(mods__draft=False, mods__publish_date__lte=now)))
        .filter(uses__gt=0)
        .order_by("-uses", "name")[:limit]
    )
