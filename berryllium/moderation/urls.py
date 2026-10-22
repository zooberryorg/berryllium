from django.urls import path

from berryllium.moderation import views

urlpatterns = [
    path("moderation/", views.overview, name="moderation_overview"),
    path("moderation/files/", views.files, name="moderation_files"),
    path("moderation/files/review/", views.files_review, name="moderation_files_review"),
    path("moderation/mods/", views.mods, name="moderation_mods"),
    path("moderation/mods/bulk/", views.mods_bulk, name="moderation_mods_bulk"),
    path("moderation/tags/", views.tags, name="moderation_tags"),
    path("moderation/tags/change/", views.tags_change, name="moderation_tags_change"),
    path("moderation/team/", views.team, name="moderation_team"),
    path("moderation/team/change/", views.team_change, name="moderation_team_change"),
]