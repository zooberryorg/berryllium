import math
import os
import re
import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from berryllium.mods.models import ModCredit

WORDS_PER_MINUTE = 200


def post_thumbnail_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"posts/thumbnails/{uuid.uuid4().hex}{ext}"


def post_file_path(instance, filename):
    return f"posts/files/{instance.post_id}/{uuid.uuid4().hex[:8]}-{os.path.basename(filename)}"


def post_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"posts/images/{instance.post_id}/{uuid.uuid4().hex}{ext}"


class Post(models.Model):
    """
    A tutorial or a news article, written in markdown.

    Definitions:
    - kind: tutorial (anyone) or news (moderators and admins)
    - body: markdown, rendered with shared.markdown_render (sanitized with nh3)
    - thumbnail: the one image shown on cards and at the top of the article; more images go in the body
    - draft / publish_date / first_published_at: same meaning as on Mod
    - is_archived_file, original_*: the post was first published elsewhere (named like Mod's fields so the
      shared general-info form and template work for both)
    - credits: collaborators and original authors, see PostCredit
    """

    class Kind(models.TextChoices):
        TUTORIAL = "tutorial", "Tutorial"
        NEWS = "news", "News"

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.TUTORIAL, db_index=True)
    title = models.CharField(max_length=200, db_index=True)
    summary = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to=post_thumbnail_path, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    tags = models.ManyToManyField("shared.Tag", blank=True, related_name="posts")
    pending_tags = models.JSONField(default=list, blank=True)

    draft = models.BooleanField(default=True, db_index=True)
    publish_date = models.DateTimeField(default=timezone.now, db_index=True)
    first_published_at = models.DateTimeField(null=True, blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    is_archived_file = models.BooleanField(default=False)
    original_release_date = models.DateField(null=True, blank=True)
    original_websites = models.ManyToManyField("shared.ArchivedWebsite", blank=True, related_name="archived_posts")

    class Meta:
        ordering = ["-publish_date"]

    def __str__(self):
        return self.title or f"Untitled post #{self.pk}"

    def get_absolute_url(self):
        return reverse("post_detail", kwargs={"post_id": self.pk})

    @property
    def status(self):
        """draft | unpublished | scheduled | published (same as Mod.status)"""
        if self.draft:
            return "unpublished" if self.first_published_at else "draft"
        if self.publish_date > timezone.now():
            return "scheduled"
        return "published"

    @property
    def reading_minutes(self):
        words = len(re.findall(r"\w+", self.body or ""))
        return max(1, math.ceil(words / WORDS_PER_MINUTE))


class PostCredit(models.Model):
    """A person credited on a post."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="credits")
    role = models.CharField(max_length=20, choices=ModCredit.Role.choices)
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="post_credits"
    )
    author = models.ForeignKey(
        "users.Author", null=True, blank=True, on_delete=models.CASCADE, related_name="post_credits"
    )
    pending_name = models.CharField(max_length=150, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["role", "order", "id"]

    def __str__(self):
        return f"{self.display_name} on post {self.post_id}"

    @property
    def display_name(self):
        if self.member_id:
            return self.member.username
        if self.author_id:
            return self.author.name
        return self.pending_name


class PostFile(models.Model):
    """A file attached to a post."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=post_file_path)
    filename = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    size = models.BigIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title or self.filename


class PostImage(models.Model):
    """An image inserted into a post's body with the editor's image button."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="body_images")
    image = models.ImageField(upload_to=post_image_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)


# stored files go with their rows
@receiver(post_delete, sender=PostFile)
def _delete_post_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


@receiver(post_delete, sender=PostImage)
def _delete_post_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(post_delete, sender=Post)
def _delete_post_thumbnail(sender, instance, **kwargs):
    if instance.thumbnail:
        instance.thumbnail.delete(save=False)
