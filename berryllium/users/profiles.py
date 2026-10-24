from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.urls import reverse

from berryllium.mods.models import Mod
from berryllium.mods.review import _labels
from berryllium.mods.settings import GALLERY_RATIO
from berryllium.shared import options
from berryllium.mods.views.explore import (
    DEFAULT_SORT,
    MAX_QUERY_LENGTH,
    SORTS,
    _card_image_path,
    _category_chips,
    published_mods,
)

PAGE_SIZE = 24


def profile_url(member=None, author=None):
    """Where a credited person's name should link to, or "" when they have no page (a pending name)."""
    if member is not None:
        return reverse("member_profile", kwargs={"username": member.username})
    if author is not None:
        if author.member_id:
            return reverse("member_profile", kwargs={"username": author.member.username})
        return reverse("author_profile", kwargs={"author_id": author.pk})
    return ""


def credit_profile_url(credit):
    return profile_url(member=credit.member if credit.member_id else None,
                       author=credit.author if credit.author_id else None)


def member_mods(member):
    """Published mods a member uploaded or is credited on (directly or through a linked Author)."""
    return published_mods().filter(
        Q(uploaded_by=member) | Q(credits__member=member) | Q(credits__author__member=member)
    ).distinct()


def author_mods(author):
    return published_mods().filter(credits__author=author).distinct()


def _stats(mods_queryset):
    return Mod.objects.filter(pk__in=mods_queryset.values("pk")).aggregate(
        mods=Count("pk"), downloads=Sum("download_count"), likes=Sum("like_count")
    )


def profile_context(request, mods_queryset):
    params = request.GET
    q = params.get("q", "").strip()[:MAX_QUERY_LENGTH]
    sort = params.get("sort", "")
    sort = sort if sort in SORTS else DEFAULT_SORT

    results = mods_queryset
    if q:
        results = results.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(tags__name__icontains=q)).distinct()
    results = (
        results.select_related("uploaded_by")
        .annotate(card_image_path=_card_image_path())
        .order_by(*SORTS[sort][1])
    )
    page = Paginator(results, PAGE_SIZE).get_page(params.get("page"))
    for mod in page.object_list:
        mod.card_image_url = default_storage.url(mod.card_image_path) if mod.card_image_path else None
        mod.category_labels = _labels(mod.category, options.category_labels("mod"))
        mod.category_chips = _category_chips(mod.category)
        mod.game_labels = _labels(mod.game, options.game_labels())

    page_query = params.copy()
    page_query.pop("page", None)
    stats = _stats(mods_queryset)
    return {
        "stats": {key: value or 0 for key, value in stats.items()},
        "q": q,
        "sort": sort,
        "sort_options": [(key, label) for key, (label, _) in SORTS.items()],
        "page": page,
        "page_range": list(page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)),
        "page_query": page_query.urlencode(),
        "gallery_ratio": GALLERY_RATIO,
    }