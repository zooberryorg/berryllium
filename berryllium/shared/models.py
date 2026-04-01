from django.db import models


class Tag(models.Model):
    """
    Simple tag model for categorizing mods.
    """

    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name