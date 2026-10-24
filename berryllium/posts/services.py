from django.db import transaction
from django.utils import timezone

from berryllium.mods.pickers import normalize_tag, resolve_pending_credits
from berryllium.posts.models import Post
from berryllium.shared.models import Tag
from berryllium.users.permissions import can_edit_post


def is_public(post):
    return not post.draft and post.publish_date <= timezone.now()


def can_view(post, user):
    """Published posts are public; drafts and scheduled posts only for people who can edit them."""
    return is_public(post) or can_edit_post(user, post)


def publish_problems(post):
    """What prevents the post from publication. Returns a list of dicts with message and section keys."""
    problems = []
    if not post.title.strip():
        problems.append({"message": "Add a title.", "section": "details"})
    if not post.summary.strip():
        problems.append({"message": "Add a summary.", "section": "details"})
    if not (post.category or "").strip():
        problems.append({"message": "Pick a category.", "section": "tags"})
    if not post.thumbnail:
        problems.append({"message": "Upload a thumbnail image.", "section": "thumbnail"})
    if not post.body.strip():
        problems.append({"message": "Write the article.", "section": "article"})
    return problems


def publish_post(post):
    """Create pending authors and tags, then publish. Only the first publish sets the date (as for mods)."""
    with transaction.atomic():
        resolve_pending_credits(post)
        for name in post.pending_tags or []:
            name = normalize_tag(name)
            if name:
                tag = Tag.objects.filter(name__iexact=name).first() or Tag.objects.create(name=name)
                post.tags.add(tag)
        post.pending_tags = []
        if post.first_published_at is None:
            if post.publish_date is None or post.publish_date <= timezone.now():
                post.publish_date = timezone.now()
            post.first_published_at = post.publish_date
        post.draft = False
        post.save(update_fields=["pending_tags", "publish_date", "first_published_at", "draft"])


def published_posts(kind=None):
    posts = Post.objects.filter(draft=False, publish_date__lte=timezone.now())
    return posts.filter(kind=kind) if kind else posts
