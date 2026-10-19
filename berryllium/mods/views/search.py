from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from berryllium.mods.pickers import person_item, tag_item, website_item
from berryllium.shared.models import ArchivedWebsite, Tag
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

