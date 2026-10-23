from berryllium.inbox.services import unread_count


def inbox_counts(request):
    """unread_messages for the inbox icon in the top bar."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return {}
    return {"unread_messages": unread_count(user)}