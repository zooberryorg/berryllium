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

# --------------------------------------------------------------------------- conversations


def conversation_between(a, b):
    """The private conversation between two members (not one with an organization)."""
    return (
        Conversation.objects.filter(organization__isnull=True)
        .filter(memberships__member=a).filter(memberships__member=b).first()
    )

def org_conversation(member, org):
    """The conversation between a member and an organization."""
    return Conversation.objects.filter(organization=org, memberships__member=member).first()


def other_member(conversation, me):
    for membership in conversation.memberships.all():
        if membership.member_id != me.pk:
            return membership.member
    return None


def membership_for(conversation_id, member):
    return (
        ConversationMember.objects.select_related("conversation")
        .filter(conversation_id=conversation_id, member=member)
        .first()
    )

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

# --------------------------------------------------------------------------- sending


def problem_sending(sender, recipient):
    """Why sender can't write to recipient right now, or empty string."""
    if recipient is None or not recipient.is_active or getattr(recipient, "is_archived", False):
        return "This account can't receive messages."
    if recipient.pk == sender.pk:
        return "You can't send a message to yourself."
    mine = usage_summary(sender)
    if mine["full"]:
        return f"Your inbox is full ({mine['used']} of {mine['limit']} messages). Delete some conversations to make room."
    if usage_summary(recipient)["full"]:
        return f"{recipient.username}'s inbox is full, so they can't receive messages right now."
    return ""


def too_soon(sender):
    last = Message.objects.filter(sender=sender).order_by("-created_at").values_list("created_at", flat=True).first()
    return bool(last and timezone.now() - last < timedelta(seconds=COOLDOWN_SECONDS))

@transaction.atomic
def start_conversation(sender, recipient):
    conversation = conversation_between(sender, recipient)
    if conversation is None:
        conversation = Conversation.objects.create()
        ConversationMember.objects.create(conversation=conversation, member=sender, last_read_at=timezone.now())
        ConversationMember.objects.create(conversation=conversation, member=recipient)
    return conversation

@transaction.atomic
def send_message(conversation, sender, recipient, body, quote=None):
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        quote_of=quote,
        quote_author=(quote.sender.username if quote.sender else "a deleted member") if quote is not None else "",
        quote_text=quote_text(quote) if quote is not None else "",
    )
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at"])
    # it shows up again for both, and the sender has read everything up to their own message
    conversation.memberships.update(is_hidden=False)
    conversation.memberships.filter(member=sender).update(last_read_at=message.created_at)

    # one notification per sender until it's read, not one per message
    if not has_unread(recipient, sender, Notification.Kind.MESSAGE):
        link = reverse("inbox_conversation", kwargs={"conversation_id": conversation.pk}) + f"#message-{message.pk}"
        transaction.on_commit(lambda: notify([recipient], sender, Notification.Kind.MESSAGE, f"{sender.username} sent you a message", link))
    return message
