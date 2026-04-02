from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class Member(AbstractUser):
    """
    Extends Django user. Pre-built fields:
    - username
    - password
    - email
    - first_name
    - last_name
    - is_staff
    - is_active
    - date_joined
    - last_login
    """
    biography = models.TextField(blank=True, max_length=500)
    is_archived = models.BooleanField(default=False)