from django.urls import path
from berryllium.mods.views import upload, explore
import berryllium.mods.hx as hx

urlpatterns = [
    # Upload form
    path("mods/upload/", upload.upload_mod, name="upload_mod"),
    path("mods/upload/s1", upload.upload_step1, name="upload_step1"),
    path("mods/upload/s2", upload.upload_step2, name="upload_step2"),
    path("mods/upload/s3", upload.upload_step3, name="upload_step3"),
    path("mods/upload/s4", upload.upload_step4, name="upload_step4"),
    # File management
    path(
        "mods/remove/<int:file_id>/",
        upload.remove_temp_file,
        name="remove_temp_file",
    ),
    # Explore mods
    path("explore/mods/", explore.mods, name="explore_mods"),
    # File Drafts
    path("mods/drafts/<int:mod_id>/", upload.open_mod_draft, name="open_mod_draft"),
    # Session management
    path("mods/upload/cancel/", upload.cancel_mod_upload, name="cancel_mod_upload"),
    # HTMX endpoints
    path("mods/validate-url/", hx.hx_process_url_field, name="hx_process_url_field"),
    path(
        "mods/toggle-group-manager/",
        hx.hx_toggle_group_manager,
        name="hx_toggle_group_manager",
    ),
    path(
        "mods/update-file-name/<int:fg_id>/<int:prefix_id>/",
        hx.hx_validate_filegroup_name,
        name="hx_validate_filegroup_name",
    ),
    path(
        "mods/update-file-description/<int:fg_id>/<int:prefix_id>/",
        hx.hx_validate_filegroup_description,
        name="hx_validate_filegroup_description",
    ),
    path(
        "mods/update-single-file-title/<int:file_id>/<int:prefix_id>/",
        hx.hx_validate_singlefile_title,
        name="hx_validate_singlefile_title",
    ),
    path(
        "mods/update-single-file-description/<int:file_id>/<int:prefix_id>/",
        hx.hx_validate_singlefile_description,
        name="hx_validate_singlefile_description",
    ),
    path(
        "mods/add-filegroup-form/<int:group_index>/",
        hx.hx_add_filegroup_form,
        name="hx_add_filegroup_form",
    ),
]
