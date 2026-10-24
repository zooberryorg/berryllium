from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render

from berryllium.mods.views.explore import published_mods
from berryllium.organizations.models import Organization
from berryllium.shared import options
from berryllium.users.directory import _mod_year, _remove_url

PAGE_SIZE = 50
SORTS = {
    "mods": "Most mods",
    "downloads": "Most downloaded",
    "members": "Most members",
    "recent": "Recently active",
    "name": "Name (A–Z)",
}
DEFAULT_SORT = "mods"
TYPES = {"managed": "Managed", "archived": "Archived"}


def collect_organizations():
    """One dict per organization, with totals from its published mods."""
    orgs = {
        org.pk: {
            "org": org, "name": org.name, "members": org.member_count, "mods": 0, "downloads": 0,
            "years": set(), "categories": set(), "games": set(), "last_published": None,
        }
        for org in Organization.objects.annotate(member_count=Count("memberships", distinct=True))
    }
    for mod in published_mods().filter(organization__isnull=False).only(
        "organization_id", "category", "game", "download_count", "publish_date", "is_archived_file", "original_release_date",
    ):
        row = orgs.get(mod.organization_id)
        if row is None:
            continue
        row["mods"] += 1
        row["downloads"] += mod.download_count
        row["years"].add(_mod_year(mod))
        row["categories"] |= set(options.keys(mod.category))
        row["games"] |= set(options.keys(mod.game))
        if row["last_published"] is None or mod.publish_date > row["last_published"]:
            row["last_published"] = mod.publish_date
    for row in orgs.values():
        row["first_year"] = min(row["years"]) if row["years"] else None
        row["last_year"] = max(row["years"]) if row["years"] else None
    return list(orgs.values())


def read_filters(params):
    sort = params.get("sort", "")
    return {
        "q": params.get("q", "").strip()[:100],
        "category": params.get("category", "") if params.get("category", "") in options.category_labels("mod") else "",
        "type": params.get("type", "") if params.get("type", "") in TYPES else "",
        "game": params.get("game", "") if params.get("game", "") in options.game_labels() else "",
        "sort": sort if sort in SORTS else DEFAULT_SORT,
    }


def apply_filters(rows, filters):
    q = filters["q"].lower()
    result = []
    for row in rows:
        org = row["org"]
        if q and q not in org.name.lower() and q not in (org.tagline or "").lower():
            continue
        if filters["category"] and filters["category"] not in row["categories"]:
            continue
        if filters["type"] and org.is_archived != (filters["type"] == "archived"):
            continue
        if filters["game"] and filters["game"] not in row["games"]:
            continue
        result.append(row)
    def name(r):
        return r["name"].lower()
    sort = filters["sort"]
    if sort == "name":
        result.sort(key=name)
    elif sort == "downloads":
        result.sort(key=lambda r: (-r["downloads"], name(r)))
    elif sort == "members":
        result.sort(key=lambda r: (-r["members"], name(r)))
    elif sort == "recent":
        # organizations without mods go last
        result.sort(key=name)
        result.sort(key=lambda r: (r["last_published"] is not None, r["last_published"] or 0), reverse=True)
    else:
        result.sort(key=lambda r: (-r["mods"], name(r)))
    return result


def organizations(request):
    params = request.GET
    filters = read_filters(params)
    everyone = collect_organizations()
    results = apply_filters(everyone, filters)
    page = Paginator(results, PAGE_SIZE).get_page(params.get("page"))

    active = []
    if filters["q"]:
        active.append({"label": f'"{filters["q"]}"', "name": "q", "value": "", "url": _remove_url(params, "q")})
    if filters["category"]:
        active.append({"label": options.category_labels("mod")[filters["category"]], "name": "category", "value": "", "url": _remove_url(params, "category")})
    if filters["type"]:
        active.append({"label": TYPES[filters["type"]], "name": "type", "value": "", "url": _remove_url(params, "type")})
    if filters["game"]:
        active.append({"label": options.game_labels()[filters["game"]], "name": "game", "value": "", "url": _remove_url(params, "game")})

    page_query = params.copy()
    page_query.pop("page", None)
    context = {
        "page": page,
        "page_range": list(page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)),
        "page_query": page_query.urlencode(),
        "filters": filters,
        "active_filters": active,
        "has_anyone": bool(everyone),
    }
    is_htmx = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
    if is_htmx:
        return render(request, "organizations/explore/results.html", context)
    context.update({
        "explore_tab": "organizations",
        "total_published": len(everyone),
        "categories": [
            {"key": key, "label": label, "icon": options.category_icons("mod").get(key, "bi-folder"),
             "count": sum(1 for r in everyone if key in r["categories"])}
            for key, label in options.mod_categories()
        ],
        "type_options": [
            {"key": key, "label": label, "icon": "bi-archive" if key == "archived" else "bi-diagram-3",
             "count": sum(1 for r in everyone if r["org"].is_archived == (key == "archived"))}
            for key, label in TYPES.items()
        ],
        "sort_options": list(SORTS.items()),
        "game_options": options.game_options(include_na=False),
    })
    return render(request, "organizations/explore/base.html", context)
