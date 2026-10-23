from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from berryllium.inbox import services
from berryllium.inbox.forms import DefaultLimitForm, MessageForm, NewMessageForm, QuotaForm
from berryllium.inbox.models import InboxQuota, InboxSettings, Message
from berryllium.users.permissions import is_site_admin, moderator_required

PAGE_SIZE = 25


def _list_context(request):
    page = Paginator(services.conversation_list(request.user), PAGE_SIZE).get_page(request.GET.get("page"))
    return {"conversations": page, "usage": services.usage_summary(request.user)}


def _conversation_url(conversation_id, message_id=None):
    url = reverse("inbox_conversation", kwargs={"conversation_id": conversation_id})
    return f"{url}#message-{message_id}" if message_id else url


@login_required
def index(request):
    return render(request, "inbox/index.html", _list_context(request))