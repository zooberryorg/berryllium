import os
import uuid
from django.db import models
from berryllium.shared.links import DEFAULT_LINK_PRESET, LINK_PRESET_CHOICES, link_preset

class Tag(models.Model):
    """
    Simple tag model for categorizing mods.
    """

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

def archived_website_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"archived_websites/{uuid.uuid4().hex}{ext}"

class ArchivedWebsite(models.Model):
    """
    A site that used to host ZT mods.

    Definitions:
    - name / slug: display name and URL-safe id (for a future website page)
    - aliases: other names the site went by, comma separated (searched by the picker)
    - description: history and notes about the site
    - url: the site's main address
    - games: games the site covered, e.g. "zt1, zt2"
    - is_offline: the site no longer exists at its address
    - is_enabled: shown in the upload form's website picker
    - est_date / closure_date: when the site opened / closed
    - former_staff: people who ran the site
    - banner / thumbnail: images for listings and a future website page
    - links: related addresses (original, Wayback Machine snapshots, mirrors), see ArchivedWebsiteLink
    """

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    aliases = models.CharField(
        max_length=300, blank=True, help_text="Other names, comma separated. Used in search."
    )
    description = models.TextField(blank=True)
    url = models.URLField(blank=True, help_text="Main address of the site.")
    games = models.CharField(max_length=50, blank=True, help_text='e.g. "zt1, zt2"')

    is_offline = models.BooleanField(default=True)
    is_enabled = models.BooleanField(default=True, help_text="Show in the upload form's website picker.")

    est_date = models.DateField(null=True, blank=True, verbose_name="established")
    closure_date = models.DateField(null=True, blank=True)

    former_staff = models.ManyToManyField(
        "users.Author", blank=True, related_name="staffed_websites"
    )

    banner = models.ImageField(upload_to=archived_website_image_path, blank=True)
    thumbnail = models.ImageField(upload_to=archived_website_image_path, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def years_active(self):
        """e.g. "1999–2008", "2003–", or "" when unknown."""
        start = self.est_date.year if self.est_date else None
        end = self.closure_date.year if self.closure_date else None
        if start and end:
            return f"{start}–{end}"
        if start:
            return f"{start}–"
        return ""

class ArchivedWebsiteLink(models.Model):
    """An address related to an archived website."""

    class Kind(models.TextChoices):
        ORIGINAL = "original", "Original address"
        WAYBACK = "wayback", "Wayback Machine snapshot"
        MIRROR = "mirror", "Mirror / backup"
        OTHER = "other", "Other"

    website = models.ForeignKey(ArchivedWebsite, on_delete=models.CASCADE, related_name="links")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    label = models.CharField(max_length=100, blank=True)
    url = models.URLField()

    def __str__(self):
        return self.label or self.url

class License(models.Model):
    """
    Model for licenses that can be applied to mods and tutorials.
    """

    name = models.CharField(max_length=150, unique=True)
    short_name = models.CharField(max_length=50, blank=True, help_text='e.g. "CC BY 4.0"')
    description = models.TextField(blank=True)
    url = models.URLField(blank=True, help_text="Where to read the full license.")
    is_enabled = models.BooleanField(default=True, help_text="Show in the upload form's license picker.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.short_name or self.name

def language_icon_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"language_icons/{uuid.uuid4().hex}{ext}"

class Language(models.Model):
    """A language a mod is available in. Can only be edited by staff. Icon is just a ico graphic."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text='Language code, e.g. "en", "pt-BR".')
    icon = models.ImageField(upload_to=language_icon_path, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
