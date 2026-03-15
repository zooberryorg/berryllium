from django.db import models
# from users.models import User
# from markdownx.models import MarkdownxField
# from tags.models import Tag


# Create your models here.
class Mod(models.Model):
    """
    Typical mod uploaded to the app
    """

    # basic info
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    summary = models.CharField(max_length=500, blank=True)
    # game info
    game = models.CharField(max_length=100)
    expansions = models.CharField(max_length=200, blank=True)

    # user relations
    # owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_mods')
    # contributors = models.ManyToManyField(User, through='users.Contributor', related_name='contributed_mods', blank=True)
    uploaded_by = models.CharField(max_length=100)

    draft = models.BooleanField(default=True)
    # tags = models.ManyToManyField(Tag, blank=True)
    version = models.CharField(max_length=100)
    # description = MarkdownxField(blank=True)

    # dates
    original_release_date = models.DateField(null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    last_updated = models.DateField(auto_now=True)
    # files
    # images = models.ManyToManyField(UploadedImage, blank=True)
    files_groups = models.ManyToManyField("FileGroup", blank=True)
    dependencies = models.ManyToManyField(
        "self",
        through="Dependency",
        symmetrical=False,
        related_name="dependent_mods_set",
        blank=True,
    )
    contents = models.TextField(blank=True)
    # archival info
    former_hosts = models.CharField(max_length=200, blank=True)
    archived_file = models.BooleanField(default=False)
    # misc
    permissions = models.CharField(max_length=200, blank=True)
    # stats
    download_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    # followers = models.ManyToManyField(User, related_name='followed_mods', blank=True)

    # permissions
    allow_fan_images = models.BooleanField(default=False)


class Dependency(models.Model):
    """
    Dependencies are files that a mod relies on; can be external link or internal reference
    """

    from_mod = models.ForeignKey(
        Mod, related_name="dependency_relationships", on_delete=models.CASCADE
    )
    dependency_mod = models.ForeignKey(
        Mod, related_name="dependent_mods", on_delete=models.CASCADE
    )
    notes = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    version = models.CharField(max_length=100, blank=True)
    is_external = models.BooleanField(default=False)
    external_url = models.URLField(blank=True)


class FileUpload(models.Model):
    """
    File uploads attached to mod pages.
    """

    file = models.FileField(upload_to="uploads/")
    date = models.DateTimeField(auto_now_add=True)
    size = models.FloatField()
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    # for orphaned uploads tracking
    upload_session = models.CharField(max_length=255, blank=True, null=True)


class FileGroup(models.Model):
    """
    By default mods have FileGroup support for the cases where multiple files need to be listed on the page. Each file needs its own metadata.
    """

    mod_id = models.ForeignKey(
        "mods.Mod", on_delete=models.CASCADE, related_name="file_groups"
    )
    name = models.CharField(max_length=255)
    files = models.ManyToManyField(
        FileUpload, through="FileGroupMembership", related_name="file_groups"
    )
    order = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        """
        File ordering
        """

        ordering = ["order"]


class FileGroupMembership(models.Model):
    """
    Through model that offers file metadata in a FileGroup, specifically file reference and order in the group.
    """

    file_group = models.ForeignKey(FileGroup, on_delete=models.CASCADE)
    uploaded_file = models.ForeignKey(FileUpload, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        """
        File ordering and unique relationships
        """

        ordering = ["order"]
        unique_together = ['file_group', 'uploaded_file']
