import os
import uuid
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from berryllium.shared.models import BaseLink
def org_logo_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"organizations/logos/{uuid.uuid4().hex}{ext}"
def org_banner_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"organizations/banners/{uuid.uuid4().hex}{ext}"

class Organization(models.Model):
    """
    A group of members that publish mods (and posts) together.
    Definitions:
    - slug: the address of its page, /orgs/<slug>/
    - description: the biography, in markdown
    - logo: the profile picture; banner: optional wide image at the top of its page
    - accepts_requests: whether members can ask to join from its page (invites always work)
    - members: through OrganizationMembership (roles and permissions)
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    tagline = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to=org_logo_path, blank=True)
    banner = models.ImageField(upload_to=org_banner_path, blank=True)
    accepts_requests = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="organizations", through="OrganizationMembership")
    class Meta:
        ordering = ["name"]
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("organization_profile", kwargs={"slug": self.slug})

    
class OrganizationMembership(models.Model):
    """
    A member's place in an organization.

    Definitions:
    - role: owner (one per organization, can do everything), co-owner (everything except deleting the
      organization and changing other co-owners) or member (only what the permissions below allow)
    - title: what they do there, shown on the organization page (e.g. "Texture artist")
    - can_publish: may publish mods and posts under the organization's name
    - can_use_inbox: may read and answer the organization's messages
    - can_edit_profile: may change the organization's page (bio, pictures, links)
    Owners and co-owners have every permission whatever these say.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        CO_OWNER = "co_owner", "Co-owner"
        MEMBER = "member", "Member"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.MEMBER)
    title = models.CharField(max_length=80, blank=True)
    can_publish = models.BooleanField(default=False)
    can_use_inbox = models.BooleanField(default=False)
    can_edit_profile = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["joined_at"]
        constraints = [models.UniqueConstraint(fields=["user", "organization"], name="org_one_membership_each")]
    def __str__(self):
        return f"{self.user_id} in {self.organization_id} ({self.role})"
    @property
    def is_manager(self):
        return self.role in (self.Role.OWNER, self.Role.CO_OWNER)
    def has(self, permission):
        """permission: "publish", "use_inbox" or "edit_profile"."""
        return self.is_manager or getattr(self, f"can_{permission}")
    
class OrganizationRequest(models.Model):
    """
    An open invitation (the organization asked a member) or join request (a member asked the organization).
    It's removed once accepted or declined.
    """
    class Kind(models.TextChoices):
        INVITE = "invite", "Invitation"
        REQUEST = "request", "Request to join"
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="requests")
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_requests")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    message = models.CharField(max_length=300, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["organization", "member"], name="org_one_open_request_each")]
    def __str__(self):
        return f"{self.kind}: {self.member_id} / {self.organization_id}"
    
class OrganizationLink(BaseLink):
    """A link on an organization's page (website, Discord, ...)."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="links")

@receiver(post_delete, sender=Organization)
def _delete_org_images(sender, instance, **kwargs):
    for image in (instance.logo, instance.banner):
        if image:
            image.delete(save=False)