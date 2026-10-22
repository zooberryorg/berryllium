from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from berryllium.mods.models import ModCredit
from berryllium.mods.pickers import picker_config
from berryllium.mods.settings import MOD_CATEGORIES, MOD_CATEGORY_ICONS
from berryllium.mods.views.explore import published_mods
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
        tags = {tag.name for tag in mod.tags.all()}
        websites = {str(site.pk) for site in mod.original_websites.all()} if mod.is_archived_file else {ZOOBERRY}
        year = _mod_year(mod)
        for key, name, member, url in _modders_of(mod):
            person = people.setdefault(key, {
                "key": key, "name": name, "member": member, "url": url, "mods": set(), "downloads": 0,
                "years": set(), "websites": set(), "categories": set(), "tags": set(), "last_published": None,
            })
            if mod.pk in person["mods"]:
                continue  # credited twice on the same mod
            person["mods"].add(mod.pk)
            person["downloads"] += mod.download_count
            person["years"].add(year)
            person["websites"] |= websites
            person["categories"] |= categories
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
        "sort": sort if sort in SORTS else DEFAULT_SORT,
    }