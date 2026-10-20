from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from berryllium.mods.pickers import person_item, tag_item, website_item
from berryllium.mods.models import Mod
from berryllium.mods.resources import license_result, mod_result
from berryllium.shared.models import ArchivedWebsite, Language, License, Tag
from berryllium.users.models import Author

MAX_QUERY_LENGTH = 100


def _query(request):
    return request.GET.get("q", "").strip()[:MAX_QUERY_LENGTH]

@login_required
@require_GET
def search_people(request):
    """Members first, then authors without an account."""
    q = _query(request)
    if not q:
        return JsonResponse({"results": []})

    User = get_user_model()
    members = (
        User.objects.filter(is_active=True)
        .filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        .order_by("username")[:15]
    )
    authors = Author.objects.filter(member__isnull=True, name__icontains=q).order_by("name")[:10]
    results = [person_item("member", m) for m in members] + [person_item("author", a) for a in authors]
    return JsonResponse({"results": results})

@login_required
@require_GET
def search_websites(request):
    """Enabled archived websites; with no query, the first 20 alphabetically."""
    q = _query(request)
    websites = ArchivedWebsite.objects.filter(is_enabled=True)
    if q:
        websites = websites.filter(Q(name__icontains=q) | Q(aliases__icontains=q))
    return JsonResponse({"results": [website_item(w) for w in websites.order_by("name")[:20]]})

@login_required
@require_GET
def search_tags(request):
    """Tags matching the query; with no query, the 20 most used tags."""
    q = _query(request)
    tags = Tag.objects.annotate(uses=Count("mods"))
    if q:
        tags = tags.filter(name__icontains=q).order_by("-uses", "name")
    else:
        tags = tags.order_by("-uses", "name")
    return JsonResponse({"results": [tag_item(t) for t in tags[:20]]})

@login_required
@require_GET
def search_mods(request):
    """Published mods by title, for dependencies. With no query, returns nothing (to avoid sending a huge list)."""
    q = _query(request)
    if not q:
        return JsonResponse({"results": []})
    mods = Mod.objects.filter(draft=False, title__icontains=q).select_related("uploaded_by")
    exclude = request.GET.get("exclude", "")
    if exclude.isdigit():
        mods = mods.exclude(pk=int(exclude))
    return JsonResponse({"results": [mod_result(m) for m in mods.order_by("title")[:20]]})


@login_required
@require_GET
def search_licenses(request):
    """Enabled licenses; with no query, all of them."""
    q = _query(request)
    licenses = License.objects.filter(is_enabled=True)
    if q:
        licenses = licenses.filter(Q(name__icontains=q) | Q(short_name__icontains=q) | Q(description__icontains=q))
    return JsonResponse({"results": [license_result(item) for item in licenses.order_by("name")[:30]]})


@login_required
@require_GET
def search_languages(request):
    """Languages by name or code; with no query, all of them."""
    q = _query(request)
    languages = Language.objects.all()
    if q:
        languages = languages.filter(Q(name__icontains=q) | Q(code__iexact=q))
    results = [
        {"value": str(lang.pk), "label": lang.name, "sublabel": lang.code}
        for lang in languages.order_by("name")[:50]
    ]
    return JsonResponse({"results": results})
