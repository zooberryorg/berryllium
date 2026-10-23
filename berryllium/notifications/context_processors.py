from berryllium.notifications.services import unread_count


def notification_counts(request):
    """`unread_notifications` for the bell in the top bar."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return {}
    return {"unread_notifications": unread_count(user)}
