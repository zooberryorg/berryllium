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
