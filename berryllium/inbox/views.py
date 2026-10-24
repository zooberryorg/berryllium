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
    from berryllium.users.settings_views import _nav  # the Control Panel menu
    page = Paginator(services.conversation_list(request.user), PAGE_SIZE).get_page(request.GET.get("page"))
    return {"conversations": page, "usage": services.usage_summary(request.user), "panel_nav": _nav(request, "inbox")}


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
    org_slug = request.GET.get("org") or request.POST.get("org")
    if org_slug:
        return _new_to_org(request, org_slug)
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

def _new_to_org(request, slug):
    """Write to an organization. Its members who may use its inbox read and answer it."""
    from berryllium.organizations.models import Organization
    org = Organization.objects.filter(slug=slug).first()
    if org is None:
        raise Http404("Organization not found.")
    existing = services.org_conversation(request.user, org)
    if existing is not None and request.method == "GET":
        return redirect(_conversation_url(existing.pk) + "#reply")
    form = MessageForm(request.POST or None, auto_id="id_message_%s", rows=8)
    problem = services.problem_sending_to_org(request.user, org) if request.method == "GET" else ""
    if request.method == "POST" and form.is_valid():
        problem = services.problem_sending_to_org(request.user, org)
        if not problem and services.too_soon(request.user):
            problem = "You're sending messages very quickly. Wait a moment and try again."
        if not problem:
            conversation = services.start_org_conversation(request.user, org)
            message = services.send_message(conversation, request.user, None, form.cleaned_data["body"])
            return redirect(_conversation_url(conversation.pk, message.pk))
    return render(request, "inbox/new.html", {**_list_context(request), "form": form, "problem": problem, "to_org": org})

@login_required
@require_http_methods(["GET", "POST"])
def conversation(request, conversation_id):
    membership = services.membership_for(conversation_id, request.user)
    if membership is None:
        raise Http404("Conversation not found.")
    convo = membership.conversation
    org = convo.organization  # set when this conversation is with an organization
    other = None if org else services.other_member(convo, request.user)
    show_all = bool(request.GET.get("all"))

    quote = None
    quote_id = request.POST.get("quote") or request.GET.get("quote")
    if quote_id and str(quote_id).isdigit():
        quote = Message.objects.select_related("sender").filter(pk=int(quote_id), conversation=convo).first()

    form = MessageForm(request.POST or None, auto_id="id_reply_%s", rows=5)
    problem = ""
    if request.method == "POST":
        if form.is_valid():
            problem = services.problem_sending_to_org(request.user, org) if org else services.problem_sending(request.user, other)
            if not problem and services.too_soon(request.user):
                problem = "You're sending messages very quickly. Wait a moment and try again."
            if not problem:
                message = services.send_message(convo, request.user, other, form.cleaned_data["body"], quote=quote)
                return redirect(_conversation_url(convo.pk, message.pk))

    shown, has_earlier = services.visible_messages(membership, show_all=show_all)
    first_unread = None
    if membership.last_read_at:
        first_unread = next((m.pk for m in shown if m.created_at > membership.last_read_at and m.sender_id != request.user.pk), None)
    services.mark_read(membership)
    return render(request, "inbox/conversation.html", {
        **_list_context(request),
        "membership": membership,
        "conversation": convo,
        "other": other,
        "thread": shown,
        "has_earlier": has_earlier,
        "first_unread": first_unread,
        "form": form,
        "quote": quote,
        "org": org,
        "problem": problem or (
            (services.problem_sending_to_org(request.user, org) if org else services.problem_sending(request.user, other))
            if request.method == "GET" else ""
        ),
    })

@login_required
@require_POST
def delete(request, conversation_id):
    membership = services.membership_for(conversation_id, request.user)
    if membership is None:
        raise Http404("Conversation not found.")
    services.clear(membership)
    messages.success(request, "Conversation deleted. The other person still has their copy.")
    return redirect("inbox")

# --------------------------------------------------------------------------- Moderation


@moderator_required
@require_http_methods(["GET", "POST"])
def limits(request):
    from berryllium.moderation.views import _nav  # the moderation menu

    settings_row = InboxSettings.load()
    default_form = DefaultLimitForm(instance=settings_row)
    quota_form = QuotaForm()
    can_change_default = is_site_admin(request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "default" and can_change_default:
            default_form = DefaultLimitForm(request.POST, instance=settings_row)
            if default_form.is_valid():
                default_form.save()
                messages.success(request, f"Inboxes now hold {settings_row.default_limit:,} messages unless a member has their own limit.")
                return redirect("moderation_inbox")
        elif action == "quota":
            quota_form = QuotaForm(request.POST)
            if quota_form.is_valid():
                quota = quota_form.save(by=request.user)
                messages.success(request, f"{quota.member.username}'s inbox now holds {quota.limit:,} messages.")
                return redirect("moderation_inbox")
        elif action == "remove" and request.POST.get("quota", "").isdigit():
            quota = InboxQuota.objects.select_related("member").filter(pk=int(request.POST["quota"])).first()
            if quota is not None:
                name = quota.member.username
                quota.delete()
                messages.success(request, f"{name} is back on the default limit.")
            return redirect("moderation_inbox")

    quotas = list(InboxQuota.objects.select_related("member", "set_by").order_by("member__username"))
    for quota in quotas:
        quota.used = services.inbox_usage(quota.member)
    return render(request, "inbox/moderation/limits.html", {
        "panel_nav": _nav(request, "moderation_inbox"),
        "settings_row": settings_row,
        "default_form": default_form,
        "quota_form": quota_form,
        "quotas": quotas,
        "can_change_default": can_change_default,
    })
