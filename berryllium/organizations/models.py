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