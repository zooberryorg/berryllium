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
