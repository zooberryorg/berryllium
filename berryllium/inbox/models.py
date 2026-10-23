from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    """
    Private messages between two members. There is one conversation per pair.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        return f"Conversation {self.pk}"