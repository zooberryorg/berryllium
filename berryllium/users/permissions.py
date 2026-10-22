from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

MODERATOR_GROUP = "Moderators"


def is_site_admin(user):
    return bool(user and user.is_authenticated and user.is_active and (user.is_superuser or user.is_staff))


def is_moderator(user):
    """Moderators and admins."""
    if not (user and user.is_authenticated and user.is_active):
        return False
    if is_site_admin(user):
        return True
    # cached on the user object for the rest of the request
    if not hasattr(user, "_is_moderator"):
        user._is_moderator = user.groups.filter(name=MODERATOR_GROUP).exists()
    return user._is_moderator


def can_edit_mod(user, mod):
    """The uploader, plus moderators and admins."""
    return bool(user and user.is_authenticated and (user.pk == mod.uploaded_by_id or is_moderator(user)))


def moderator_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_moderator(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_site_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper