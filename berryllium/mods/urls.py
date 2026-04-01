from django.urls import path
from berryllium.mods.views import create, explore
import berryllium.mods.validations as validations

urlpatterns = [
    # Upload form (CREATE)
    path("mods/create/", create.ModCreateLanding.as_view(), name="mod_create_landing"),
    path("mods/create/s1", create.ModCreateCategorization.as_view(), name="mod_create_categorization"),
    path("mods/create/s2", create.ModCreateFiles.as_view(), name="mod_create_files"),
    path("mods/create/s3", create.ModCreateImages.as_view(), name="mod_create_images"),
    path(
        "mods/create/s4",
        create.ModCreateDescription.as_view(),
        name="mod_create_description",
    ),
    path("mods/create/s6", create.upload_step3, name="upload_step3"),
    # ---------------------------------------------- File management
    path(
        "mods/remove/<int:file_id>/",
        create.remove_temp_file,
        name="remove_temp_file",
    ),
    # ---------------------------------------------- Explore mods (READ)
    path("explore/mods/", explore.mods, name="explore_mods"),
    # ---------------------------------------------- Session management
    path("mods/create/cancel/", create.cancel_mod_upload, name="cancel_mod_upload"),
    # ---------------------------------------------- HTMX endpoints
    path(
        "mods/validate-url/",
        validations.hx_process_url_field,
        name="hx_process_url_field",
    ),
    path(
        "mods/toggle-group-manager/",
        validations.hx_toggle_group_manager,
        name="hx_toggle_group_manager",
    ),
    path(
        "mods/update-file-name/<int:fg_id>/",
        validations.hx_validate_filegroup_name,
        name="hx_validate_filegroup_name",
    ),
    path(
        "mods/update-file-description/<int:fg_id>/",
        validations.hx_validate_filegroup_description,
        name="hx_validate_filegroup_description",
    ),
    path(
        "mods/update-single-file-title/<int:file_id>/",
        validations.hx_validate_singlefile_title,
        name="hx_validate_singlefile_title",
    ),
    path(
        "mods/update-single-file-description/<int:file_id>/",
        validations.hx_validate_singlefile_description,
        name="hx_validate_singlefile_description",
    ),
    path(
        "mods/add-filegroup-form/",
        validations.hx_add_filegroup_form,
        name="hx_add_filegroup_form",
    ),
    path(
        "mods/remove-filegroup-form/<int:fg_id>/",
        validations.hx_remove_filegroup_form,
        name="hx_remove_filegroup_form",
    ),
    path(
        "mods/add-file-to-group/",
        validations.hx_add_file_to_group,
        name="hx_add_file_to_group",
    ),
    path(
        "mods/empty-filegroups-warning/",
        validations.hx_empty_filegroups_warning,
        name="hx_empty_filegroups_warning",
    ),
    path(
        "mods/remove-empty-filegroups/",
        validations.hx_remove_empty_filegroups,
        name="hx_remove_empty_filegroups",
    ),
    path(
        "mods/move-filegroup-up/<int:current_index>/",
        validations.hx_move_filegroup_up,
        name="hx_move_filegroup_up",
    ),
    path(
        "mods/move-filegroup-down/<int:current_index>/",
        validations.hx_move_filegroup_down,
        name="hx_move_filegroup_down",
    ),
    path(
        "mods/file-order-update-in-group/",
        validations.hx_update_file_order_in_group,
        name="hx_update_file_order_in_group",
    ),
    path(
        "mods/upload-images/",
        validations.hx_upload_images,
        name="hx_upload_images",
    ),
    path(
        "mods/remove-temp-image/<int:image_id>/",
        validations.hx_remove_temp_image,
        name="hx_remove_temp_image",
    ),
    path(
        "mods/update-image-title/<int:image_id>/",
        validations.hx_update_image_title,
        name="hx_update_image_title",
    ),
    path(
        "mods/update-image-caption/<int:image_id>/",
        validations.hx_update_image_caption,
        name="hx_update_image_caption",
    ),
    path(
        "mods/set-cover-image/<int:image_id>/",
        validations.hx_set_cover_image,
        name="hx_set_cover_image",
    ),
]
