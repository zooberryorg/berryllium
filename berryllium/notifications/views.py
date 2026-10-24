import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from berryllium.notifications.models import Notification
from berryllium.notifications.services import MENU_SIZE, mark_read, safe_url, unread_count

PAGE_SIZE = 30
KIND_ICONS = {"comment": "bi-chat-left-text", "reply": "bi-reply", "quote": "bi-quote", "message": "bi-envelope"}


def _decorate(items):
    for item in items:
        item.icon = KIND_ICONS.get(item.kind, "bi-bell")
    return items


def _menu(request):
    items = _decorate(list(Notification.objects.filter(recipient=request.user).select_related("actor")[:MENU_SIZE]))
    return render(request, "notifications/menu.html", {"items": items, "unread": unread_count(request.user)})

@login_required
@require_GET
def menu(request):
    """The bell in the top bar. Loads last few notifications."""
    return _menu(request)

@require_GET
def badge(request):
    """
    Unread count for the top bar bell, checked every 30 seconds while the tab is visible.
    It also tells the page the count (notificationsCount), so an open bell menu can reload.
    """
    if not request.user.is_authenticated:
        # signed out in another tab: 286 tells htmx to stop polling (instead of swapping in the login page)
        return HttpResponse(status=286)
    count = unread_count(request.user)
    response = render(request, "notifications/badge.html", {"unread_notifications": count})
    response["HX-Trigger"] = json.dumps({"notificationsCount": count})
    return response

@login_required
@require_GET
def index(request):
    show = request.GET.get("show", "")
    items = Notification.objects.filter(recipient=request.user).select_related("actor")
    if show == "unread":
        items = items.filter(read_at__isnull=True)
    page = Paginator(items, PAGE_SIZE).get_page(request.GET.get("page"))
    _decorate(page.object_list)
    return render(request, "notifications/index.html", {"page": page, "show": show, "unread": unread_count(request.user)})

@login_required
@require_GET
def open_notification(request, notification_id):
    """Mark it read, then go to what it's about."""
    item = get_object_or_404(Notification, pk=notification_id, recipient=request.user)
    mark_read(Notification.objects.filter(pk=item.pk))
    return redirect(safe_url(item.url))

@login_required
@require_POST
def mark_all_read(request):
    mark_read(Notification.objects.filter(recipient=request.user))
    if request.headers.get("HX-Request") and request.POST.get("from") == "menu":
        return _menu(request)
    return redirect("notifications")