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
    Through model for organization memberships.

    Definitions:
    - user: the user who is a member of the organization
    - organization: the organization the user is a member of
    - role: the role of the user in the organization (e.g., owner, contributor)
    - joined_at: when the user joined the organization
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default="contributor")
    joined_at = models.DateTimeField(auto_now_add=True)