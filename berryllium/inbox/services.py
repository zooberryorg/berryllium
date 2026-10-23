from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.urls import reverse
from django.utils import timezone

from berryllium.comments.services import quote_text
from berryllium.inbox.models import Conversation, ConversationMember, InboxQuota, InboxSettings, Message
from berryllium.notifications.models import Notification
from berryllium.notifications.services import has_unread, notify

MAX_LENGTH = 10000
COOLDOWN_SECONDS = 3
SHOWN_MESSAGES = 100  # newest messages shown in a conversation


# --------------------------------------------------------------------------- size


def inbox_limit(member):
    quota = InboxQuota.objects.filter(member=member).values_list("limit", flat=True).first()
    return quota if quota is not None else InboxSettings.load().default_limit


def inbox_usage(member):
    """Messages this member can still see: everything after they last deleted each conversation."""
    mine = ConversationMember.objects.filter(conversation=OuterRef("conversation"), member=member).filter(
        Q(cleared_at__isnull=True) | Q(cleared_at__lt=OuterRef("created_at"))
    )
    return Message.objects.filter(Exists(mine)).count()


def usage_summary(member):
    used, limit = inbox_usage(member), inbox_limit(member)
    percent = 100 if limit == 0 else min(100, round(used * 100 / limit))
    return {"used": used, "limit": limit, "percent": percent, "full": used >= limit, "nearly_full": percent >= 80}

# --------------------------------------------------------------------------- unread


def _unread_messages(member):
    """messages from others that arrived after this member last opened the conversation"""
    mine = ConversationMember.objects.filter(conversation=OuterRef("conversation"), member=member).filter(
        Q(last_read_at__isnull=True) | Q(last_read_at__lt=OuterRef("created_at"))
    )
    return Message.objects.exclude(sender=member).filter(Exists(mine))


def unread_count(member):
    if not member.is_authenticated:
        return 0
    return _unread_messages(member).count()

def conversation_list(member):
    """This member's conversations, newest first, with the other person, the last message and an unread count."""
    last = Message.objects.filter(conversation=OuterRef("conversation")).order_by("-created_at")
    rows = list(
        ConversationMember.objects.filter(member=member, is_hidden=False)
        .select_related("conversation")
        .prefetch_related("conversation__memberships__member")
        .annotate(
            last_body=Subquery(last.values("body")[:1]),
            last_sender_id=Subquery(last.values("sender")[:1]),
        )
        .order_by("-conversation__last_message_at")
    )
    unread = dict(
        _unread_messages(member).order_by().values("conversation_id").annotate(n=Count("pk")).values_list("conversation_id", "n")
    )
    for row in rows:
        row.other = other_member(row.conversation, member)
        row.unread = unread.get(row.conversation_id, 0)
    return rows


def visible_messages(membership, show_all=False):
    """Returns tuple with (messages, has_earlier) for this member, oldest first."""
    messages = membership.conversation.messages.select_related("sender")
    if membership.cleared_at:
        messages = messages.filter(created_at__gt=membership.cleared_at)
    if show_all:
        return list(messages), False
    newest = list(messages.order_by("-created_at")[: SHOWN_MESSAGES + 1])
    has_earlier = len(newest) > SHOWN_MESSAGES
    return list(reversed(newest[:SHOWN_MESSAGES])), has_earlier


def mark_read(membership):
    membership.last_read_at = timezone.now()
    membership.save(update_fields=["last_read_at"])


def clear(membership):
    """Delete a conversation for this member only."""
    now = timezone.now()
    membership.cleared_at = membership.last_read_at = now
    membership.is_hidden = True
    membership.save(update_fields=["cleared_at", "last_read_at", "is_hidden"])