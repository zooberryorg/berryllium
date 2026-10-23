from django.contrib.auth.decorators import login_required
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

