from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from berryllium.mods.views.explore import published_mods
from berryllium.posts.models import Post
from berryllium.shared import options
from berryllium.shared.models import ArchivedWebsite, ArchivedWebsiteLink
from berryllium.users.directory import _remove_url
from berryllium.users.profiles import profile_context, profile_url

PAGE_SIZE = 50
SORTS = {
    "mods": "Most archived mods",
    "name": "Name (A–Z)",
    "oldest": "Oldest first",
    "newest": "Newest first",
}
DEFAULT_SORT = "mods"
STATUSES = {"online": "Still online", "offline": "Offline"}
LINK_ICONS = {
    ArchivedWebsiteLink.Kind.ORIGINAL: "bi-globe2",
    ArchivedWebsiteLink.Kind.WAYBACK: "bi-clock-history",
    ArchivedWebsiteLink.Kind.MIRROR: "bi-hdd-stack",
    ArchivedWebsiteLink.Kind.OTHER: "bi-link-45deg",
}


def _archived_mods(website=None):
    mods = published_mods().filter(is_archived_file=True)
    return mods.filter(original_websites=website) if website is not None else mods


def _with_counts(websites):
    published = _archived_mods().values("pk")
    return websites.annotate(
        mod_count=Count("archived_mods", filter=Q(archived_mods__in=published), distinct=True),
        staff_count=Count("former_staff", distinct=True),
    )


def read_filters(params):
    sort = params.get("sort", "")
    return {
        "q": params.get("q", "").strip()[:100],
        "status": params.get("status", "") if params.get("status", "") in STATUSES else "",
        "game": params.get("game", "") if params.get("game", "") in options.game_labels() else "",
        "sort": sort if sort in SORTS else DEFAULT_SORT,
    }


def apply_filters(websites, filters):
    if filters["q"]:
        websites = websites.filter(Q(name__icontains=filters["q"]) | Q(aliases__icontains=filters["q"]))
    if filters["status"]:
        websites = websites.filter(is_offline=filters["status"] == "offline")
    if filters["game"]:
        key = filters["game"]
        websites = websites.filter(Q(games__regex=rf"(^|,\s*){key}(\s*,|$)"))
    # websites without an opening date go last either way
    order = {
        "name": ["name"],
        "oldest": [F("est_date").asc(nulls_last=True), "name"],
        "newest": [F("est_date").desc(nulls_last=True), "name"],
    }
    return websites.order_by(*order.get(filters["sort"], ["-mod_count", "name"]))


def _describe(website):
    website.game_labels = options.labels_for(website.games, options.game_labels())
    return website


@require_GET
def explore(request):
    params = request.GET
    filters = read_filters(params)
    everyone = _with_counts(ArchivedWebsite.objects.all())
    results = apply_filters(everyone, filters)
    page = Paginator(results, PAGE_SIZE).get_page(params.get("page"))
    for website in page.object_list:
        _describe(website)

    active = []
    if filters["q"]:
        active.append({"label": f'"{filters["q"]}"', "name": "q", "value": "", "url": _remove_url(params, "q")})
    if filters["status"]:
        active.append({"label": STATUSES[filters["status"]], "name": "status", "value": "", "url": _remove_url(params, "status")})
    if filters["game"]:
        active.append({"label": options.game_labels()[filters["game"]], "name": "game", "value": "", "url": _remove_url(params, "game")})

    page_query = params.copy()
    page_query.pop("page", None)
    total = ArchivedWebsite.objects.count()
    context = {
        "page": page,
        "page_range": list(page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)),
        "page_query": page_query.urlencode(),
        "filters": filters,
        "active_filters": active,
        "has_anyone": bool(total),
    }
    is_htmx = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
    if is_htmx:
        return render(request, "shared/websites/results.html", context)
    context.update({
        "explore_tab": "websites",
        "total_websites": total,
        "status_options": [
            {"key": key, "label": label, "icon": "bi-wifi-off" if key == "offline" else "bi-wifi",
             "count": ArchivedWebsite.objects.filter(is_offline=key == "offline").count()}
            for key, label in STATUSES.items()
        ],
        "sort_options": list(SORTS.items()),
        "game_options": options.game_options(include_na=False),
    })
    return render(request, "shared/websites/base.html", context)


@require_GET
def profile(request, slug):
    """A website's profiel page"""
    website = get_object_or_404(ArchivedWebsite, slug=slug)
    context = profile_context(request, _archived_mods(website))
    is_htmx = request.headers.get("HX-Request") and not request.headers.get("HX-History-Restore-Request")
    if is_htmx:
        return render(request, "users/profile/results.html", context)
    staff = [
        {"name": author.name, "url": profile_url(author=author), "member": author.member}
        for author in website.former_staff.select_related("member").order_by("name")
    ]
    articles = (
        Post.objects.filter(original_websites=website, draft=False, publish_date__lte=timezone.now())
        .order_by("-publish_date")[:10]
    )
    downloads = _archived_mods(website).aggregate(total=Sum("download_count"))["total"] or 0
    context.update({
        "website": _describe(website),
        "display_name": website.name,
        "downloads": downloads,
        "links": [{"url": link.url, "label": link.label or link.get_kind_display(), "icon": LINK_ICONS.get(link.kind, "bi-link-45deg")}
                  for link in website.links.all()],
        "staff": staff,
        "articles": list(articles),
    })
    return render(request, "shared/websites/profile.html", context)
