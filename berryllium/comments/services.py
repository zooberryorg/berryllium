"""
Comment rules: who may comment, posting (with notifications), deleting, and the comment counts on cards.
"""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from berryllium.comments import targets
from berryllium.comments.models import Comment
from berryllium.notifications.models import Notification
from berryllium.notifications.services import notify
from berryllium.users.permissions import is_moderator

PAGE_SIZE = 15 # top-level comments per page. their replies always come along
MAX_LENGTH = 10000
QUOTE_LENGTH = 1500 # longer comments are cut when quoted
COOLDOWN_SECONDS = 10 # between two comments from the same member


def comments_for(obj):
    return Comment.objects.filter(content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk)


def refresh_count(obj):
    """Recount the comments shown on cards (deleted ones don't count)."""
    count = comments_for(obj).filter(is_deleted=False).count()
    type(obj).objects.filter(pk=obj.pk).update(comment_count=count)
    obj.comment_count = count
    return count


def can_comment(obj, user):
    return bool(user.is_authenticated and targets.is_public(obj) and obj.comments_enabled)


def can_edit(comment, user):
    return bool(user.is_authenticated and not comment.is_deleted and comment.author_id == user.pk)


def can_delete(comment, user):
    return bool(user.is_authenticated and not comment.is_deleted and (comment.author_id == user.pk or is_moderator(user)))


def _with_replies(queryset):
    replies = Comment.objects.select_related("author").order_by("created_at")
    return queryset.select_related("author").prefetch_related(Prefetch("replies", queryset=replies))


def threads_page(obj, number=1):
    """Top-level comments, newest first, each with its replies (oldest first)."""
    top = _with_replies(comments_for(obj).filter(parent__isnull=True).order_by("-created_at"))
    return Paginator(top, PAGE_SIZE).get_page(number)


def get_thread(thread_id):
    return _with_replies(Comment.objects.filter(pk=thread_id)).first()


def too_soon(user):
    last = Comment.objects.filter(author=user).order_by("-created_at").values_list("created_at", flat=True).first()
    return bool(last and timezone.now() - last < timedelta(seconds=COOLDOWN_SECONDS))


def quote_text(comment):
    """the quoted part cut to a reasonable length"""
    body = comment.body.strip()
    return body if len(body) <= QUOTE_LENGTH else body[:QUOTE_LENGTH].rstrip() + "…"

@transaction.atomic
def create_comment(obj, author, body, reply_to=None, quote=None):
    """reply_to and quote must be comments on the same target (the view checks)."""
    parent = None
    if reply_to is not None:
        parent = reply_to.parent or reply_to
    comment = Comment.objects.create(
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        author=author,
        parent=parent,
        reply_to=reply_to,
        reply_to_name=reply_to.author.username if reply_to is not None and reply_to.author else "",
        quote_of=quote,
        quote_author=(quote.author.username if quote.author else "a deleted member") if quote is not None else "",
        quote_text=quote_text(quote) if quote is not None else "",
        body=body,
    )
    refresh_count(obj)
    transaction.on_commit(lambda: _notify(obj, comment, reply_to, quote, parent))
    return comment

def _notify(obj, comment, reply_to, quote, parent):
    """Quoted people hear first, then the people replied to. owners only hear about new top-level comments."""
    name = comment.author.username
    title = obj.title or "Untitled"
    link = f"{targets.url(obj)}#comment-{comment.pk}"
    done = set()
    if quote is not None and quote.author:
        sent = notify([quote.author], comment.author, Notification.Kind.QUOTE, f"{name} quoted you on “{title}”", link)
        done |= {row.recipient_id for row in sent}
    if reply_to is not None:
        people = [p for p in (reply_to.author, parent.author) if p is not None and p.pk not in done]
        notify(people, comment.author, Notification.Kind.REPLY, f"{name} replied to you on “{title}”", link)
    else:
        text = f"{name} commented on your {targets.label(obj)} “{title}”"
        # several comments in a row from one person: one notification until it's read
        waiting = set(Notification.objects.filter(kind=Notification.Kind.COMMENT, text=text, read_at__isnull=True).values_list("recipient_id", flat=True))
        people = [p for p in targets.owners(obj) if p.pk not in done and p.pk not in waiting]
        notify(people, comment.author, Notification.Kind.COMMENT, text, link)