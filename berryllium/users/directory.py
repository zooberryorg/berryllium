from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import render
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from berryllium.mods.models import ModCredit
from berryllium.mods.pickers import picker_config
from berryllium.mods.settings import GAME_OPTIONS, MOD_CATEGORIES, MOD_CATEGORY_ICONS
from berryllium.mods.views.explore import PERIODS, published_mods
from berryllium.shared.fields import proper_case
from berryllium.shared.models import ArchivedWebsite
from berryllium.users.profiles import profile_url

PAGE_SIZE = 50
MAX_TAGS = 10
ZOOBERRY = "zooberry"
SORTS = {
    "mods": "Most mods",
    "downloads": "Most downloaded",
    "recent": "Recently active",
    "name": "Name (A–Z)",
}
DEFAULT_SORT = "mods"


def _mod_year(mod):
    if mod.is_archived_file and mod.original_release_date:
        return mod.original_release_date.year
    return mod.publish_date.year


def _modders_of(mod):
    """key, name, member or None, url for each person credited as a modder of this mod."""
    role = ModCredit.Role.ORIGINAL_AUTHOR if mod.is_archived_file else ModCredit.Role.COLLABORATOR
    people = []
    for credit in mod.credits.all():
        if credit.role != role:
            continue
        if credit.member_id:
            people.append((f"m:{credit.member_id}", credit.member.username, credit.member, profile_url(member=credit.member)))
        elif credit.author_id and credit.author.member_id:
            member = credit.author.member
            people.append((f"m:{member.pk}", member.username, member, profile_url(member=member)))
        elif credit.author_id:
            people.append((f"a:{credit.author_id}", credit.author.name, None, profile_url(author=credit.author)))
    if not people and not mod.is_archived_file and mod.uploaded_by_id:
        member = mod.uploaded_by
        people.append((f"m:{member.pk}", member.username, member, profile_url(member=member)))
    return people

def collect_modders():
    """One dict per person, from every published mod."""
    credits = Prefetch("credits", queryset=ModCredit.objects.select_related("member", "author__member"))
    mods = published_mods().select_related("uploaded_by").prefetch_related(credits, "tags", "original_websites")
    people = {}
    for mod in mods:
        categories = {key.strip() for key in (mod.category or "").split(",") if key.strip()}
        games = {key.strip() for key in (mod.game or "").split(",") if key.strip()}
        tags = {tag.name for tag in mod.tags.all()}
        websites = {str(site.pk) for site in mod.original_websites.all()} if mod.is_archived_file else {ZOOBERRY}
        year = _mod_year(mod)
        for key, name, member, url in _modders_of(mod):
            person = people.setdefault(key, {
                "key": key, "name": name, "member": member, "url": url, "mods": set(), "downloads": 0,
                "years": set(), "websites": set(), "categories": set(), "games": set(), "tags": set(), "last_published": None,
            })
            if mod.pk in person["mods"]:
                continue  # credited twice on the same mod
            person["mods"].add(mod.pk)
            person["downloads"] += mod.download_count
            person["years"].add(year)
            person["websites"] |= websites
            person["categories"] |= categories
            person["games"] |= games
            person["tags"] |= tags
            if person["last_published"] is None or mod.publish_date > person["last_published"]:
                person["last_published"] = mod.publish_date
    for person in people.values():
        person["mod_count"] = len(person["mods"])
        person["first_year"], person["last_year"] = min(person["years"]), max(person["years"])
    return list(people.values())

def _int(value):
    return int(value) if str(value).isdigit() else None


def read_filters(params):
    sort = params.get("sort", "")
    return {
        "q": params.get("q", "").strip()[:100],
        "category": params.get("category", "") if params.get("category", "") in dict(MOD_CATEGORIES) else "",
        "tags": list(dict.fromkeys(proper_case(t) for t in params.getlist("tag") if t.strip()))[:MAX_TAGS],
        "year_from": _int(params.get("from", "")),
        "year_to": _int(params.get("to", "")),
        "websites": [w for w in params.getlist("website") if w == ZOOBERRY or w.isdigit()],
        "game": params.get("game", "") if params.get("game", "") in dict(GAME_OPTIONS) else "",
        "period": params.get("period", "") if params.get("period", "") in PERIODS else "",
        "sort": sort if sort in SORTS else DEFAULT_SORT,
    }

def apply_filters(people, filters):
    tags_lower = {t.lower() for t in filters["tags"]}
    since = timezone.now() - timedelta(days=PERIODS[filters["period"]][1]) if filters["period"] else None
    result = []
    for person in people:
        if filters["q"] and filters["q"].lower() not in person["name"].lower():
            continue
        if filters["category"] and filters["category"] not in person["categories"]:
            continue
        if tags_lower and not tags_lower <= {t.lower() for t in person["tags"]}:
            continue
        # active at any point in the range: their first..last year overlaps it
        if filters["year_from"] and person["last_year"] < filters["year_from"]:
            continue
        if filters["year_to"] and person["first_year"] > filters["year_to"]:
            continue
        if filters["websites"] and not set(filters["websites"]) & person["websites"]:
            continue
        if filters["game"] and filters["game"] not in person["games"]:
            continue
        if since and person["last_published"] < since:
            continue
        result.append(person)
    sort = filters["sort"]
    if sort == "name":
        result.sort(key=lambda p: p["name"].lower())
    elif sort == "downloads":
        result.sort(key=lambda p: (-p["downloads"], p["name"].lower()))
    elif sort == "recent":
        result.sort(key=lambda p: (p["last_published"], p["name"].lower()), reverse=True)
    else:
        result.sort(key=lambda p: (-p["mod_count"], p["name"].lower()))
    return result

def _remove_url(params, key, value=None):
    query = params.copy()
    query.pop("page", None)
    if value is None:
        query.pop(key, None)
    else:
        query.setlist(key, [v for v in query.getlist(key) if v != value])
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"

def modders(request):
    params = request.GET
    filters = read_filters(params)
    everyone = collect_modders()
    results = apply_filters(everyone, filters)

    site_names = {str(site.pk): site.name for site in ArchivedWebsite.objects.all()}
    site_names[ZOOBERRY] = "ZooBerry"

    page = Paginator(results, PAGE_SIZE).get_page(params.get("page"))
    for person in page.object_list:
        labels = sorted((site_names.get(w, "") for w in person["websites"] if w != ZOOBERRY), key=str.lower)
        person["website_labels"] = (["ZooBerry"] if ZOOBERRY in person["websites"] else []) + [l for l in labels if l]

    active = []
    if filters["q"]:
        active.append({"label": f'"{filters["q"]}"', "name": "q", "value": "", "url": _remove_url(params, "q")})
    if filters["category"]:
        active.append({"label": dict(MOD_CATEGORIES)[filters["category"]], "name": "category", "value": "", "url": _remove_url(params, "category")})
    for tag in filters["tags"]:
        active.append({"label": tag, "name": "tag", "value": tag, "url": _remove_url(params, "tag", tag)})
    if filters["year_from"]:
        active.append({"label": f"Active since {filters['year_from']}", "name": "from", "value": "", "url": _remove_url(params, "from")})
    if filters["year_to"]:
        active.append({"label": f"Active until {filters['year_to']}", "name": "to", "value": "", "url": _remove_url(params, "to")})
    if filters["game"]:
        active.append({"label": dict(GAME_OPTIONS)[filters["game"]], "name": "game", "value": "", "url": _remove_url(params, "game")})
    if filters["period"]:
        active.append({"label": f"Last published {PERIODS[filters['period']][0].lower()}", "name": "period", "value": "", "url": _remove_url(params, "period")})
    for website in filters["websites"]:
        active.append({"label": site_names.get(website, website), "name": "website", "value": website, "url": _remove_url(params, "website", website)})

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
        return render(request, "users/modders/results.html", context)

    years = sorted({year for person in everyone for year in person["years"]})
    year_options = [(str(year), str(year)) for year in range(years[0], max(years[-1], timezone.now().year) + 1)] if years else []
    used_sites = {w for person in everyone for w in person["websites"]}
    context.update({
        "explore_tab": "modders",
        "total_published": len(everyone),
        "categories": [
            {"key": key, "label": label, "icon": MOD_CATEGORY_ICONS.get(key, "bi-folder"),
             "count": sum(1 for p in everyone if key in p["categories"])}
            for key, label in MOD_CATEGORIES
        ],
        "website_options": sorted(
            ({"key": key, "label": site_names.get(key, key), "count": sum(1 for p in everyone if key in p["websites"])}
             for key in used_sites),
            key=lambda option: (option["key"] != ZOOBERRY, option["label"].lower()),
        ),
        "year_options": year_options,
        "year_from": str(filters["year_from"] or ""),
        "year_to": str(filters["year_to"] or ""),
        "sort_options": list(SORTS.items()),
        "game_options": [option for option in GAME_OPTIONS if option[0] != "na"],
        "period_options": [(key, label) for key, (label, _) in PERIODS.items()],
        "tag_picker": picker_config(
            name="tag",
            search_url=reverse("explore_search_tags"),
            items=[{"value": t, "label": t} for t in filters["tags"]],
            title="Filter by tags",
            placeholder="Search tags...",
            empty_text="No tags match.",
        ),
    })
    return render(request, "users/modders/base.html", context)