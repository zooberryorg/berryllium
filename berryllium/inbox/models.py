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