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

    # images = models.ManyToManyField(UploadedImage, blank=True)
    contents = models.TextField(blank=True)

    # archival info
    former_hosts = models.CharField(max_length=200, blank=True)
    archived_file = models.BooleanField(default=False)

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

    mod = models.ForeignKey(
        Mod, related_name="dependencies", on_delete=models.CASCADE
    )
    notes = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    version = models.CharField(max_length=100, blank=True)
    is_external = models.BooleanField(default=False)
    external_url = models.URLField(blank=True)


class FileGroup(models.Model):
    """
    By default mods have FileGroup support for the cases where multiple files need to be listed on the page. Each file needs its own metadata.
    """

    mod = models.ForeignKey(Mod, on_delete=models.CASCADE, related_name="file_groups")
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        """
        File ordering
        """

        ordering = ["order"]

    def __str__(self):
        return f"{self.mod.title} - {self.name}"


class FileUpload(models.Model):
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
        max_length=20, choices=Status.choices, default=Status.PENDING
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
        FileGroup, on_delete=models.CASCADE, related_name="files"
    )
    order = models.PositiveIntegerField(default=0)

    # files
    staged_file = models.FileField(upload_to="uploads/")  # temp file for processing
    url = models.URLField(blank=True)  # url after processing

    # preliminary metadata; possible use for directory listings vs proper file uploads
    is_external = models.BooleanField(default=False)

    # metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    size = models.BigIntegerField()  # size in bytes
    filename = models.CharField(max_length=255) # name of the file as uploaded
    description = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True) # optional title for the file that replaces the filename in listings

    class Meta:
        """
        File ordering
        """

        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title or self.filename or self.staged_file.name} - {self.filegroup.name}"
