from django.db import models

# Create your models here.
class Organization(models.Model):
    """
    Represents an organization that can have multiple mods under it.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField("auth.User", related_name="organizations", through="OrganizationMembership")

    def __str__(self):
        return self.name
    
class OrganizationMembership(models.Model):
    """
    Through model for organization memberships.

    Definitions:
    - user: the user who is a member of the organization
    - organization: the organization the user is a member of
    - role: the role of the user in the organization (e.g., owner, contributor)
    - joined_at: when the user joined the organization
    """

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default="contributor")
    joined_at = models.DateTimeField(auto_now_add=True)