import re
from datetime import timedelta

from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import render
from django.utils import timezone

from berryllium.mods.models import Mod, ModImage
from berryllium.mods.review import _labels
from berryllium.mods.settings import GALLERY_RATIO, GAME_OPTIONS, MOD_CATEGORIES, MOD_CATEGORY_ICONS
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

def _category_chips(stored):
    """ Category chips for a mod's card, based on the stored CSV field. """
    labels = dict(MOD_CATEGORIES)
    keys = [key.strip() for key in (stored or "").split(",") if key.strip()]
    return [{"label": labels.get(key, key), "icon": MOD_CATEGORY_ICONS.get(key, "bi-folder")} for key in keys]

def _card_image_path():
    """The image shown on a mod's card: the picked thumbnail, otherwise the first gallery image."""
    return Subquery(
        ModImage.objects.filter(mod=OuterRef("pk"))
        .order_by("-is_thumbnail", "order", "id")
        .values("image")[:1]
    )

def mods(request):
    """Explore > Mods."""
    params = request.GET
    filters = _read_filters(params)
    base = published_mods()

    results = (
        _apply_filters(base, filters)
        .select_related("uploaded_by")
        .prefetch_related("tags")
        .annotate(card_image_path=_card_image_path())
    )
    page = Paginator(results, PAGE_SIZE).get_page(params.get("page"))
    for mod in page.object_list:
        mod.category_labels = _labels(mod.category, MOD_CATEGORIES)
        mod.category_chips = _category_chips(mod.category)
        mod.game_labels = _labels(mod.game, GAME_OPTIONS)
        mod.card_image_url = default_storage.url(mod.card_image_path) if mod.card_image_path else None

    page_range = list(page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1))

    page_query = params.copy()
    page_query.pop("page", None)

    context = {
        "page": page,
        "page_range": page_range,
        "gallery_ratio": GALLERY_RATIO,
        "page_query": page_query.urlencode(),
        "filters": filters,
        "active_filters": _active_filters(params, filters),
        "has_any_mods": base.exists(),
        "sort_options": [(key, label) for key, (label, _) in SORTS.items()],
        "period_options": [(key, label) for key, (label, _) in PERIODS.items()],
        "game_options": [option for option in GAME_OPTIONS if option[0] != "na"],
    }

    is_htmx = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
    if is_htmx:
        return render(request, "mods/explore/results.html", context)

    context["categories"] = _category_counts(base)
    context["total_published"] = base.count()
    context["popular_tags"] = list(_popular_tags())
    context["popular_tag_names"] = {tag.name for tag in context["popular_tags"]}
    context["explore_tab"] = "mods"
    return render(request, "mods/explore/base.html", context)
