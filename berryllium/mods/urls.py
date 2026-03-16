from django.urls import path
from .views import upload, explore

urlpatterns = [
    # Upload form
    path("mods/upload/", upload.upload_mod, name="upload_mod"),
    path("mods/upload/s1", upload.upload_step1, name="upload_step1"),
    path("mods/upload/s2", upload.upload_step2, name="upload_step2"),
    path("mods/upload/s3", upload.upload_step3, name="upload_step3"),
    # Explore mods
    path("explore/mods/", explore.mods, name="explore_mods"),
]
