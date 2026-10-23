from datetime import timedelta

from django.utils import timezone

from berryllium.notifications.models import Notification

MENU_SIZE = 8
KEEP_DAYS = 90  # read notifications older than this are removed when new ones are created


def notify(recipients, actor, kind, text, url):
    """
    Notify each recipient once. The user never notifies themselves, and inactive accounts are skipped.
    `url` must be a path on this site, e.g. "/mods/12/#comment-40".
    """
    seen, rows = set(), []
    for member in recipients:
        if member is None or member.pk in seen or not member.is_active:
            continue
        if actor is not None and member.pk == actor.pk:
            continue
        seen.add(member.pk)
        rows.append(Notification(recipient=member, actor=actor, kind=kind, text=text[:300], url=url[:500]))
    if rows:
        Notification.objects.bulk_create(rows)
        _prune([row.recipient_id for row in rows])
    return rows


def _prune(member_ids):
    cutoff = timezone.now() - timedelta(days=KEEP_DAYS)
    Notification.objects.filter(recipient_id__in=member_ids, read_at__lt=cutoff).delete()


def unread_count(member):
    if not member.is_authenticated:
        return 0
    return Notification.objects.filter(recipient=member, read_at__isnull=True).count()


def has_unread(member, actor, kind):
    """Used to avoid stacking up one notification per message from the same person."""
    return Notification.objects.filter(recipient=member, actor=actor, kind=kind, read_at__isnull=True).exists()


def mark_read(queryset):
    return queryset.filter(read_at__isnull=True).update(read_at=timezone.now())


def safe_url(url):
    """Only follow links that stay on this site."""
    return url if url.startswith("/") and not url.startswith("//") else "/"
