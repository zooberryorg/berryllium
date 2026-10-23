import os
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Comment(models.Model):
    """
    A comment on a mod or a post (the `target`). Threads are one level deep.

    Definitions:
    - parent: the top-level comment of the thread (None for a top-level comment)
    - reply_to: the comment this one answers, which can be the parent or another reply in the thread.
      reply_to_name keeps the name for "replying to @name" if that comment is deleted later.
    - quote_*: an optional quote of another comment, copied when posting so it doesn't change afterwards
    - is_deleted: a top-level comment that still has replies is blanked instead of removed, so the
      thread stays readable. Everything else is removed for real.
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reply_to_name = models.CharField(max_length=150, blank=True)

    quote_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    quote_author = models.CharField(max_length=150, blank=True)
    quote_text = models.TextField(blank=True)

    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_by_moderator = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["content_type", "object_id", "parent"], name="comment_target_parent_idx")]

    def __str__(self):
        return f"Comment {self.pk} by {self.author_id}"

    @property
    def thread_id(self):
        return self.parent_id or self.pk


def uploaded_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"uploads/markdown/{uuid.uuid4().hex}{ext}"

class UploadedImage(models.Model):
    """An image added with the editor's image button in a comment or a message."""

    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_images")
    image = models.ImageField(upload_to=uploaded_image_path)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return self.image.name