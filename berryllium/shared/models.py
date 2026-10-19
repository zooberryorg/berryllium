import os
import uuid
from django.db import models


class Tag(models.Model):
    """
    Simple tag model for categorizing mods.
    """

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

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
