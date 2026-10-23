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

class ConversationMember(models.Model):
    """
    One member's side of a conversation.
    - last_read_at: messages after this are unread
    - cleared_at: "Delete conversation" hides everything before this, for this member only. The other
      member keeps their copy. A new message brings the conversation back (is_hidden goes back to False).
    """

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="memberships")
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_memberships")
    last_read_at = models.DateTimeField(null=True, blank=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "member"], name="inbox_one_membership_each")]

    def __str__(self):
        return f"{self.member_id} in {self.conversation_id}"

class Message(models.Model):
    """A message. Quotes work like comment quotes: copied when sent."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_messages")
    body = models.TextField()
    quote_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    quote_author = models.CharField(max_length=150, blank=True)
    quote_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message {self.pk} in {self.conversation_id}"

class InboxSettings(models.Model):
    """Site-wide inbox settings. Admins can change them in cp."""

    default_limit = models.PositiveIntegerField(default=500, help_text="How many messages a member's inbox can hold.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "inbox settings"

    def __str__(self):
        return f"Inbox limit {self.default_limit}"

    @classmethod
    def load(cls):
        settings_row, _ = cls.objects.get_or_create(pk=1)
        return settings_row

class InboxQuota(models.Model):
    """A different inbox size for one member, set by a moderator or admin."""

    member = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inbox_quota")
    limit = models.PositiveIntegerField()
    note = models.CharField(max_length=200, blank=True)
    set_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.member_id}: {self.limit}"