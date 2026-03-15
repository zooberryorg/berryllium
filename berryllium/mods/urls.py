from django.urls import path
from . import views

urlpatterns = [path("mods/upload/", views.upload_mod, name="upload_mod")]
