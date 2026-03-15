from django.urls import path
from .views import upload

urlpatterns = [
    path("mods/upload/", upload.upload_mod, name="upload_mod"),
    path("mods/upload/s1", upload.upload_step1, name="upload_step1")
]
    