from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    e.g. "animalover replied to your comment on Savannah Rocks".

    The text and link are stored when it's created, so it still reads correctly if the mod or comment
    changes later.
    """

    class Kind(models.TextChoices):
        COMMENT = "comment", "New comment"
        REPLY = "reply", "Reply"
        QUOTE = "quote", "Quote"
        MESSAGE = "message", "Message"
        ORGANIZATION = "organization", "Organization"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    text = models.CharField(max_length=300)
    url = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read_at"], name="notif_recipient_read_idx")]

    def __str__(self):
        return f"{self.recipient_id}: {self.text}"

    @property
    def is_unread(self):
        return self.read_at is None
