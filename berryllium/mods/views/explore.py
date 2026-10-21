import re
from datetime import timedelta
from urllib.parse import urlparse

from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from berryllium.mods.models import Mod, ModDependency, ModImage, ModLicense
from berryllium.mods.pickers import picker_config
from berryllium.mods.review import _labels
from berryllium.mods.settings import GALLERY_RATIO, GAME_OPTIONS, MOD_CATEGORIES, MOD_CATEGORY_ICONS
from berryllium.shared.fields import proper_case
from berryllium.shared.models import License, Tag

PAGE_SIZE = 24
MAX_QUERY_LENGTH = 100
MAX_TAGS = 10
MAX_DEPENDS = 10
EXTERNAL_PREFIX = "ext:"  # <mod_id> or <ext:url> in a dependency field means "external"

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
        "tags": list(dict.fromkeys(proper_case(tag) for tag in params.getlist("tag") if tag.strip()))[:MAX_TAGS],
        "depends": list(dict.fromkeys(
            value.strip() for value in params.getlist("depends")
            if value.strip().isdigit() or (value.startswith(EXTERNAL_PREFIX) and len(value) > len(EXTERNAL_PREFIX))
        ))[:MAX_DEPENDS],
        "license": params.get("license", "") if params.get("license", "").isdigit() else "",
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
        queryset = queryset.filter(tags__name__iexact=tag)
    for value in filters["depends"]:
        if value.startswith(EXTERNAL_PREFIX):
            deps = ModDependency.objects.filter(is_external=True, external_url=value[len(EXTERNAL_PREFIX):])
        else:
            deps = ModDependency.objects.filter(is_external=False, ref_id=int(value))
        queryset = queryset.filter(pk__in=deps.values("parent_id"))
    if filters["license"]:
        queryset = queryset.filter(pk__in=ModLicense.objects.filter(license_id=int(filters["license"])).values("mod_id"))
    return queryset.order_by(*SORTS[filters["sort"]][1])

def _active_filters(params, filters, depends_items, license_obj):
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
        active.append({"label": f"{tag}", "name": "tag", "value": tag, "url": _remove_url(params, "tag", tag)})
    for item in depends_items:
        active.append({"label": f"Needs {item['label']}", "name": "depends", "value": item["value"],
                       "url": _remove_url(params, "depends", item["value"])})
    if license_obj:
        active.append({"label": str(license_obj), "name": "license", "value": "",
            "url": _remove_url(params, "license")})
    return active

def _category_counts(base):
    return [
        {"key": key, "label": label, "icon": MOD_CATEGORY_ICONS.get(key, "bi-folder"),
         "count": base.filter(_csv_has("category", key)).count()}
        for key, label in MOD_CATEGORIES
    ]

def _license_counts():
    now = timezone.now()
    licenses = License.objects.annotate(
        count=Count(
            "mod_licenses__mod",
            filter=Q(mod_licenses__mod__draft=False, mod_licenses__mod__publish_date__lte=now),
            distinct=True,
        )
    ).filter(Q(is_enabled=True) | Q(count__gt=0))
    return [
        {"key": str(item.pk), "label": item.short_name or item.name, "title": item.name, "count": item.count}
        for item in licenses.order_by("name")
    ]

def _plural(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"

def _host(url):
    return urlparse(url).netloc.removeprefix("www.") or url

def _card_image_path():
    """The image shown on a mod's card: the picked thumbnail, otherwise the first gallery image."""
    return Subquery(
        ModImage.objects.filter(mod=OuterRef("pk"))
        .order_by("-is_thumbnail", "order", "id")
        .values("image")[:1]
    )

# picker items

def _tag_result(name, uses=None):
    return {"value": name, "label": name, "sublabel": _plural(uses, "mod") if uses is not None else ""}

def _mod_dependency_result(mod, dependents=None):
    sublabel = "Mod" + (f" · needed by {_plural(dependents, 'mod')}" if dependents is not None else "")
    return {"value": str(mod.pk), "label": mod.title, "sublabel": sublabel}

def _external_dependency_result(url, title, dependents=None):
    sublabel = f"External · {_host(url)}" + (f" · needed by {_plural(dependents, 'mod')}" if dependents is not None else "")
    return {"value": f"{EXTERNAL_PREFIX}{url}", "label": title or _host(url), "sublabel": sublabel}

def _depends_items(values):
    """Pills for the "Depends on" values in the URL. Values that no longer match anything are dropped."""
    mod_ids = [int(v) for v in values if v.isdigit()]
    urls = [v[len(EXTERNAL_PREFIX):] for v in values if v.startswith(EXTERNAL_PREFIX)]
    mods = published_mods().in_bulk(mod_ids)
    titles = dict(
        ModDependency.objects.filter(is_external=True, external_url__in=urls)
        .values("external_url").annotate(shown_title=Max("title")).values_list("external_url", "shown_title")
    )
    items = []
    for value in values:
        if value.isdigit() and int(value) in mods:
            items.append(_mod_dependency_result(mods[int(value)]))
        elif value.startswith(EXTERNAL_PREFIX) and value[len(EXTERNAL_PREFIX):] in titles:
            url = value[len(EXTERNAL_PREFIX):]
            items.append(_external_dependency_result(url, titles[url]))
    return items

# picker search endpoints

@require_GET
def search_tags(request):
    """Tags on published mods, most used first."""
    q = request.GET.get("q", "").strip()[:MAX_QUERY_LENGTH]
    now = timezone.now()
    tags = Tag.objects.annotate(uses=Count("mods", filter=Q(mods__draft=False, mods__publish_date__lte=now), distinct=True))
    tags = tags.filter(uses__gt=0)
    if q:
        tags = tags.filter(name__icontains=q)
    return JsonResponse({"results": [_tag_result(t.name, t.uses) for t in tags.order_by("-uses", "name")[:20]]})


@require_GET
def search_dependencies(request):
    """
    Things that published mods depend on, most needed first.
    """
    q = request.GET.get("q", "").strip()[:MAX_QUERY_LENGTH]
    now = timezone.now()
    published_parent = Q(required_by__parent__draft=False, required_by__parent__publish_date__lte=now)
    mods = published_mods().annotate(
        dependents=Count("required_by__parent", filter=published_parent & Q(required_by__is_external=False), distinct=True)
    ).filter(dependents__gt=0)
    externals = ModDependency.objects.filter(
        is_external=True, parent__draft=False, parent__publish_date__lte=now
    ).exclude(external_url="")
    if q:
        mods = mods.filter(title__icontains=q)
        externals = externals.filter(Q(title__icontains=q) | Q(external_url__icontains=q))
    externals = externals.values("external_url").annotate(shown_title=Max("title"), dependents=Count("parent", distinct=True))
    ranked = [(m.dependents, m.title.lower(), _mod_dependency_result(m, m.dependents))
              for m in mods.order_by("-dependents", "title")[:15]]
    ranked += [(e["dependents"], (e["shown_title"] or e["external_url"]).lower(),
                _external_dependency_result(e["external_url"], e["shown_title"], e["dependents"]))
               for e in externals.order_by("-dependents", "shown_title")[:10]]
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return JsonResponse({"results": [row[2] for row in ranked[:20]]})

def _category_chips(stored):
    """ Category chips for a mod's card, based on the stored CSV field. """
    labels = dict(MOD_CATEGORIES)
    keys = [key.strip() for key in (stored or "").split(",") if key.strip()]
    return [{"label": labels.get(key, key), "icon": MOD_CATEGORY_ICONS.get(key, "bi-folder")} for key in keys]

def mods(request):
    """Explore > Mods."""
    params = request.GET
    filters = _read_filters(params)
    base = published_mods()

     # drop filter values that don't point at anything
    license_obj = License.objects.filter(pk=filters["license"]).first() if filters["license"] else None
    if not license_obj:
        filters["license"] = ""
    depends_items = _depends_items(filters["depends"])
    filters["depends"] = [item["value"] for item in depends_items]

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
