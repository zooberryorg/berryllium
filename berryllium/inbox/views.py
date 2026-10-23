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

@login_required
@require_http_methods(["GET", "POST"])
def new(request):
    """Creates a new conversation. If one already exists, redirect to it."""
    if request.method == "GET" and request.GET.get("to"):
        recipient = get_user_model().objects.filter(username__iexact=request.GET["to"], is_active=True).first()
        if recipient is not None and recipient.pk != request.user.pk:
            existing = services.conversation_between(request.user, recipient)
            if existing is not None:
                return redirect(_conversation_url(existing.pk) + "#reply")
    form = NewMessageForm(request.POST or None, initial={"to": request.GET.get("to", "")}, auto_id="id_message_%s", rows=8)
    problem = ""
    if request.method == "POST" and form.is_valid():
        recipient = form.cleaned_data["to"]
        problem = services.problem_sending(request.user, recipient)
        if not problem and services.too_soon(request.user):
            problem = "You're sending messages very quickly. Wait a moment and try again."
        if not problem:
            conversation = services.start_conversation(request.user, recipient)
            message = services.send_message(conversation, request.user, recipient, form.cleaned_data["body"])
            return redirect(_conversation_url(conversation.pk, message.pk))
    return render(request, "inbox/new.html", {**_list_context(request), "form": form, "problem": problem})

