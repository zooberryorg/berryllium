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
        ConversationMember.objects.select_related("conversation", "conversation__organization")
        .filter(conversation_id=conversation_id, member=member)
        .first()
    )

def org_side(conversation_id, org):
    """The organization's shared side of one of its conversations."""
    return (
        ConversationMember.objects.select_related("conversation", "conversation__organization")
        .filter(conversation_id=conversation_id, organization=org, member__isnull=True)
        .first()
    )

def _rows(sides):
    last = Message.objects.filter(conversation=OuterRef("conversation")).order_by("-created_at")
    return list(
        sides.filter(is_hidden=False)
        .select_related("conversation", "conversation__organization")
        .prefetch_related("conversation__memberships__member")
        .annotate(
            last_body=Subquery(last.values("body")[:1]),
            last_sender_id=Subquery(last.values("sender")[:1]),
        )
        .order_by("-conversation__last_message_at")
    )

def _counts(messages):
    return dict(messages.order_by().values("conversation_id").annotate(n=Count("pk")).values_list("conversation_id", "n"))

def conversation_list(member):
    """
    This member's conversations, newest first. Each row has other (the other member) or organization
    (when it's with an organization), the last message, an unread count and its url.
    """
    rows = _rows(ConversationMember.objects.filter(member=member))
    unread = _counts(_unread_messages(member))
    for row in rows:
        row.organization = row.conversation.organization
        row.other = None if row.organization else other_member(row.conversation, member)
        row.unread = unread.get(row.conversation_id, 0)
        row.url = reverse("inbox_conversation", kwargs={"conversation_id": row.conversation_id})
    return rows

# --------------------------------------------------------------------------- an organization's inbox

def _org_unread_messages(org):
    """Messages from outside members the organization hasn't read yet."""
    side = ConversationMember.objects.filter(conversation=OuterRef("conversation"), organization=org, member__isnull=True).filter(
        Q(last_read_at__isnull=True) | Q(last_read_at__lt=OuterRef("created_at"))
    )
    return Message.objects.filter(conversation__organization=org, sent_as__isnull=True).filter(Exists(side))

def org_unread_count(org):
    return _org_unread_messages(org).count()

def org_conversation_list(org):
    rows = _rows(ConversationMember.objects.filter(organization=org, member__isnull=True))
    unread = _counts(_org_unread_messages(org))

    for row in rows:
        row.organization = None
        row.other = next((side.member for side in row.conversation.memberships.all() if side.member_id), None)
        row.unread = unread.get(row.conversation_id, 0)
        row.url = reverse("organization_conversation", kwargs={"slug": org.slug, "conversation_id": row.conversation_id})
    return rows


def visible_messages(membership, show_all=False):
    """Returns tuple with (messages, has_earlier) for this member, oldest first."""
    messages = membership.conversation.messages.select_related("sender", "sent_as")
    if membership.cleared_at:
        messages = messages.filter(created_at__gt=membership.cleared_at)
    if show_all:
        return list(messages), False
    newest = list(messages.order_by("-created_at")[: SHOWN_MESSAGES + 1])
    has_earlier = len(newest) > SHOWN_MESSAGES
    return list(reversed(newest[:SHOWN_MESSAGES])), has_earlier


def messages_after(membership, after_id):
    """Messages that arrived after after_id, oldest first. an open conversation checks for these."""
    messages = membership.conversation.messages.select_related("sender", "sent_as").filter(pk__gt=after_id)
    if membership.cleared_at:
        messages = messages.filter(created_at__gt=membership.cleared_at)
    return list(messages.order_by("created_at", "pk")[:SHOWN_MESSAGES])


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


def problem_sending(sender, recipient, as_org=None):
    """
    Why sender can't write to recipient right now, or empty string.
    as_org: answering for an organization, so the sender's own inbox size doesn't matter.
    """
    if recipient is None or not recipient.is_active or getattr(recipient, "is_archived", False):
        return "This account can't receive messages."
    if recipient.pk == sender.pk:
        return "You can't send a message to yourself."
    if as_org is None:
        mine = usage_summary(sender)
        if mine["full"]:
            return f"Your inbox is full ({mine['used']} of {mine['limit']} messages). Delete some conversations to make room."
    if usage_summary(recipient)["full"]:
        return f"{recipient.username}'s inbox is full, so they can't receive messages right now."
    return ""

def problem_sending_to_org(sender, org):
    """Organizations have no size limit; the sender's own inbox still has to have room."""
    if org.is_archived:
        return f"{org.name} is an archived organization, so it can't receive messages."
    if org.memberships.filter(user=sender).exists():
        return f"You're a member of {org.name}. Its messages are in its inbox, under Organizations in your Control Panel."
    mine = usage_summary(sender)
    if mine["full"]:
        return f"Your inbox is full ({mine['used']} of {mine['limit']} messages). Delete some conversations to make room."
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
def start_org_conversation(sender, org):
    conversation = org_conversation(sender, org)
    if conversation is None:
        conversation = Conversation.objects.create(organization=org)
        ConversationMember.objects.create(conversation=conversation, member=sender, last_read_at=timezone.now())
        ConversationMember.objects.create(conversation=conversation, organization=org)
    return conversation

@transaction.atomic
def send_message(conversation, sender, recipient, body, quote=None, as_org=None):
    """
    recipient: the member written to (None when writing to an organization).
    as_org: the organization the sender answers for, from its inbox.
    """
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        sent_as=as_org,
        body=body,
        quote_of=quote,
        quote_author=(quote.sender.username if quote.sender else "a deleted member") if quote is not None else "",
        quote_text=quote_text(quote) if quote is not None else "",
    )
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at"])
    # it shows up again for both, and the sender's side has read everything up to their own message
    conversation.memberships.update(is_hidden=False)
    if as_org is not None:
        conversation.memberships.filter(organization=as_org, member__isnull=True).update(last_read_at=message.created_at)
    else:
        conversation.memberships.filter(member=sender).update(last_read_at=message.created_at)

    # one notification per sender until it's read, not one per message
    org = conversation.organization
    if org is not None and as_org is None:
        # a member wrote to an organization: everyone who reads its inbox hears about it
        link = reverse("organization_conversation", kwargs={"slug": org.slug, "conversation_id": conversation.pk}) + f"#message-{message.pk}"
        from berryllium.organizations.services import inbox_readers
        readers = [m for m in inbox_readers(org) if not has_unread(m, sender, Notification.Kind.MESSAGE)]
        transaction.on_commit(lambda: notify(readers, sender, Notification.Kind.MESSAGE, f"{sender.username} sent {org.name} a message", link))
    elif recipient is not None and not has_unread(recipient, sender, Notification.Kind.MESSAGE):
        link = reverse("inbox_conversation", kwargs={"conversation_id": conversation.pk}) + f"#message-{message.pk}"
        text = f"{as_org.name} answered your message" if as_org is not None else f"{sender.username} sent you a message"
        transaction.on_commit(lambda: notify([recipient], sender, Notification.Kind.MESSAGE, text, link))
    return message
