"""
What can be commented on, and the few things comments need to know about it.
Adding a new kind of target means adding it to KINDS and to each function below.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from berryllium.mods.models import Mod, ModCredit
from berryllium.posts.models import Post
from berryllium.users.permissions import can_edit_mod, can_edit_post, is_moderator

KINDS = {"mod": Mod, "post": Post}


def kind_of(obj):
    return "mod" if isinstance(obj, Mod) else "post"


def get_target(kind, pk):
    model = KINDS.get(kind)
    if model is None:
        raise Http404("Nothing to comment on.")
    return get_object_or_404(model.objects.select_related("uploaded_by"), pk=pk)


def is_public(obj):
    return not obj.draft and obj.publish_date <= timezone.now()


def can_manage(obj, user):
    """Who can turn comments off and on: whoever can edit the mod or post (its uploader, moderators, admins)."""
    return can_edit_mod(user, obj) if isinstance(obj, Mod) else can_edit_post(user, obj)


def can_view(obj, user):
    return is_public(obj) or can_manage(obj, user) or is_moderator(user)


def url(obj):
    if isinstance(obj, Mod):
        return reverse("mod_detail", kwargs={"mod_id": obj.pk})
    return obj.get_absolute_url()


def label(obj):
    """"mod", "tutorial" or "news post", for sentences like "Comments are turned off for this mod"."""
    if isinstance(obj, Mod):
        return "mod"
    return "news post" if obj.kind == Post.Kind.NEWS else "tutorial"


def owners(obj):
    """Members who made it. The uploader and credited collaborators with an account. They're told about new comments."""
    people = {}
    if obj.uploaded_by_id:
        people[obj.uploaded_by_id] = obj.uploaded_by
    credits = obj.credits.filter(role=ModCredit.Role.COLLABORATOR).select_related("member", "author__member")
    for credit in credits:
        member = credit.member or (credit.author.member if credit.author_id else None)
        if member is not None:
            people.setdefault(member.pk, member)
    return list(people.values())
