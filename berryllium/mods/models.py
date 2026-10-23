import os
import uuid
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from markdownx.models import MarkdownxField
from django.db.models.signals import post_delete
from django.dispatch import receiver

from berryllium import settings
from berryllium.shared.models import Tag, BaseLink
# from users.models import User
# from tags.models import Tag


def staged_path(instance, filename):
    return f"uploads/staged/{instance.filegroup.mod_id}/{filename}"

def mod_thumbnail_path(instance, filename):
    # no longer used, but kept for old migrations (for now)
    ext = os.path.splitext(filename)[1].lower()
    return f"mod_logos/{uuid.uuid4().hex}{ext}"

class Mod(models.Model):
    """
    Typical mod uploaded to the app

    Definitions:
    - title: the name of the mod
    - category: mod category (e.g. animals, buildings, etc.)
    - summary: short summary of the mod
    - is_external: whether the mod is an external link instead of a file upload
    - external_url: if is_external is true, the url of the mod
    - game: the game the mod is for (zt1 or zt2 for now)
    - expansions: exp compatibility
    - draft: is the listing published or not
    - version: optional version info for the mod
    - description: detailed description of the mod, supports markdown
    - submission_date: date the mod was submitted
    - last_updated: date the mod was last updated
    - contents: itemized list of mod contents, used for search indexing
    - original_websites: archived websites the mod was originally published on (archival mods)
    - is_archived_file: whether the mod is an archived file (e.g. from a dead hosting site)
    - original_release_date: original release date of the mod, used for archival mods
    - download_count: number of times the mod has been downloaded
    - like_count: number of likes the mod has received
    - allow_fan_images: whether to allow fan images to be attached to the mod page
    - use_file_groups: whether to use file groups for the mod (for multiple files with metadata)
    - pending_tags: new tag names typed in the upload form; created when the mod is published
    - credits: collaborators and original authors, see ModCredit

    Examples:
    - Mod.objects.filter(game='zt2', category='animals') -> all animal mods for Zoo Tycoon 2
    - Mod.files -> all files attached to the mod through ModFileGroups

    """

    # basic info
    title = models.CharField(max_length=200, db_index=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    summary = models.CharField(max_length=500, blank=True)

    # is mod a directory link instead of a file upload?
    is_external = models.BooleanField(default=False, db_index=True)
    external_url = models.URLField(blank=True)

    # game info
    game = models.CharField(max_length=100, db_index=True)
    expansions = models.CharField(max_length=200, blank=True, db_index=True)

    # user relations
    # contributors = models.ManyToManyField(User, through='users.Contributor', related_name='contributed_mods', blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_mods",
    )
    draft = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True, through="ModTag", related_name="mods")
    version = models.CharField(max_length=100)
    description = MarkdownxField(blank=True)
    prlicense = models.CharField(max_length=100, blank=True)

    # dates
    submission_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(default=timezone.now)
    first_published_at = models.DateTimeField(null=True, blank=True)

    contents = models.TextField(blank=True)

    # archival info
    original_websites = models.ManyToManyField(
        "shared.ArchivedWebsite", blank=True, related_name="archived_mods"
    )
    is_archived_file = models.BooleanField(default=False)
    original_release_date = models.DateField(null=True, blank=True)
    comment_count = models.PositiveIntegerField(default=0)  # kept up to date by comments.services.refresh_count

    # comments
    comments_enabled = models.BooleanField(default=True)
    comments = GenericRelation("comments.Comment")

    # stats
    download_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    # followers = models.ManyToManyField(User, related_name='followed_mods', blank=True)

    # permissions
    allow_fan_images = models.BooleanField(default=False)

    # form data
    use_file_groups = models.BooleanField(default=False)
    pending_tags = models.JSONField(default=list, blank=True)
    languages = models.ManyToManyField("shared.Language", blank=True, related_name="mods")

    @property
    def files(self):
        return ModFile.objects.filter(filegroup__mod=self)

    @property
    def status(self):
        """
        - draft: never published
        - unpublished: was published, then moved back to drafts
        - scheduled: published with a publish date in the future
        - published: live
        """
        if self.draft:
            return "unpublished" if self.first_published_at else "draft"
        if self.publish_date and self.publish_date > timezone.now():
            return "scheduled"
        return "published"
    
    @property
    def file_groups(self):
        return ModFileGroup.objects.filter(mod=self)

class ModCredit(models.Model):
    """
    A person credited on a mod, in order.

    Definitions:
    - member: a site account
    - author: an Author without an account (e.g. original creator of an archived mod)
    - pending_name: a new author typed into the upload form; turned into an Author
      when the mod is published
    """

    class Role(models.TextChoices):
        COLLABORATOR = "collaborator", "Collaborator"
        ORIGINAL_AUTHOR = "original_author", "Original author"

    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="credits")
    role = models.CharField(max_length=20, choices=Role.choices)
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="mod_credits",
    )
    author = models.ForeignKey(
        "users.Author",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="mod_credits",
    )
    pending_name = models.CharField(max_length=150, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["role", "order", "id"]

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()}) on {self.mod_id}"

    @property
    def display_name(self):
        if self.member_id:
            return self.member.username
        if self.author_id:
            return self.author.name
        return self.pending_name


class ModDependency(models.Model):
    """
    Dependencies are files that a mod relies on; can be external link or internal reference
    Definitions:
    - parent: the mod that has the dependency
    - ref: the mod that is being depended on (can be null if external)
    - notes: any notes about the dependency
    - required: whether the dependency is required or optional
    - version: optional version info for the dependency
    - is_external: whether the dependency is an external link or an internal reference
    - external_url: if is_external is true, the url of the dependency

    Examples:
    - ModA.dependencies.all() -> all dependencies for ModA
    - ModB.required_by.all() -> all mods that require ModB
    """

    parent = models.ForeignKey(
        Mod, related_name="dependencies", on_delete=models.CASCADE
    )
    ref = models.ForeignKey(
        Mod,
        related_name="required_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    version = models.CharField(max_length=100, blank=True)
    is_external = models.BooleanField(default=False)
    external_url = models.URLField(blank=True)
    title = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.display_title

    @property
    def display_title(self):
        if self.ref_id:
            return self.ref.title
        return self.title or self.external_url

class ModLicense(models.Model):
    """
    A license applied to a mod.
    """

    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="licenses")
    license = models.ForeignKey("shared.License", on_delete=models.PROTECT, related_name="mod_licenses")
    context = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.license} on {self.mod_id}"

class ModAttribution(models.Model):
    """
    Credit for work used in a mod by people who weren't involved in making it,
    for example "models sourced from XYZ" or "original textures by ABC".
    """

    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="attributions")
    title = models.CharField(max_length=200)
    url = models.URLField(max_length=500, blank=True)
    authors = models.CharField(max_length=300)
    note = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title} by {self.authors}"

class ModLink(BaseLink):
    """A link shown on a mod page (mirror, Discord, donations...)."""

    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="links")

    class Meta(BaseLink.Meta):
        pass

class ModTag(models.Model):
    """
    Through model for Mod tags.

    Definitions:
    - mod: the mod being tagged
    - tag: the tag being applied
    - created_at: when the tag was applied
    - created_by: who applied the tag
    - upvotes: number of upvotes for the tag on the mod (too few upvotes may indicate 
    the tag is not relevant to the mod and should be removed)
    """
    mod = models.ForeignKey(Mod, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255, blank=True)  # change to user later
    upvotes = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("mod", "tag")


class ModFileGroup(models.Model):
    """
    By default mods have ModFileGroup support for the cases where multiple files
    need to be listed on the page. Each file needs its own metadata.
    """

    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="file_groups")
    name = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)

    class Meta:
        """
        File ordering
        """

        ordering = ["order"]

    def __str__(self):
        return f"{self.mod.title} - {self.name}"

    @property
    def files(self):
        return self.fileupload_set.all()


class ModFile(models.Model):
    """
    File uploads attached to mod pages.
    """

    # moderation
    class Status(models.TextChoices):
        """
        Status of file processing. Reasons: AV scan, bug check, etc.
        Definitions:
        - PENDING: File uploaded but not yet processed
        - PROCESSING: File has been opened and is being processed
        - APPROVED: File has been approved and is live on the site
        - FAILED: File failed processing
        """

        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    moderated_at = models.DateTimeField(blank=True, null=True)
    moderation_notes = models.TextField(blank=True)
    # approved_by = models.ForeignKey(
    #     User,
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True,
    #     related_name="approved_files",
    # )

    # filegroup
    filegroup = models.ForeignKey(
        ModFileGroup, on_delete=models.CASCADE, related_name="files"
    )
    order = models.PositiveIntegerField(default=0)

    # files
    staged_file = models.FileField(
        upload_to=staged_path, null=True, blank=True
    )  # temp file for processing, null after processing
    url = models.URLField(blank=True, null=True)  # url after processing
    file_hash = models.CharField(
        max_length=64, blank=True
    )  # file hash for integrity check

    # metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    size = models.BigIntegerField(null=True, blank=True)  # size in bytes
    filename = models.CharField(
        max_length=255, blank=True
    )  # name of the file as uploaded
    description = models.TextField(blank=True)
    title = models.CharField(
        max_length=255, blank=True, null=True
    )  # optional title for the file that replaces the filename in listings
    version = models.CharField(max_length=100, blank=True)

    class Meta:
        """
        File ordering
        """

        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title or self.filename or (self.staged_file.name if self.staged_file else None) or f'File #{self.pk}'} - {self.filegroup.name}"


class ModImage(models.Model):
    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="mod_images/")
    title = models.CharField(max_length=255, blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_by = models.CharField(max_length=255, blank=True)  # change to user later
    is_thumbnail = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.mod.title} - Image {self.order}"

def description_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"mod_description/{instance.mod_id}/{uuid.uuid4().hex}{ext}"

class ModDescriptionImage(models.Model):
    """An image inserted into a mod's markdown description."""
    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="description_images")
    image = models.ImageField(upload_to=description_image_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

@receiver(post_delete, sender=ModDescriptionImage)
def delete_description_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)