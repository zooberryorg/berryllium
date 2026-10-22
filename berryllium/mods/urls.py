from django.urls import path
from berryllium.mods.views import create, detail, explore, search
import berryllium.mods.validations as validations

urlpatterns = [
    # Upload form (CREATE)
    path("mods/draft/", create.ModDraftView.as_view(), name="mod_create_draft"),
    path("mods/edit/<int:mod_id>/", create.ModCreateLanding.as_view(), name="mod_create_landing"),
    path("mods/edit/<int:mod_id>/categorization", create.ModCreateCategorization.as_view(), name="mod_create_categorization"),
    path("mods/edit/<int:mod_id>/files", create.ModCreateFiles.as_view(), name="mod_create_files"),
    path("mods/edit/<int:mod_id>/images", create.ModCreateImages.as_view(), name="mod_create_images"),
    path("mods/edit/<int:mod_id>/general", create.ModCreateGeneralInfo.as_view(), name="mod_create_general"),
    path(
        "mods/edit/<int:mod_id>/description",
        create.ModCreateDescription.as_view(),
        name="mod_create_description",
    ),
    path("mods/edit/<int:mod_id>/resources", create.ModCreateResources.as_view(), name="mod_create_resources"),
    path("mods/edit/<int:mod_id>/review", create.ModCreateReview.as_view(), name="mod_create_review"),
    # ---------------------------------------------- Search endpoints
    path("search/people/", search.search_people, name="search_people"),
    path("search/websites/", search.search_websites, name="search_websites"),
    path("search/tags/", search.search_tags, name="search_tags"),
    path("search/mods/", search.search_mods, name="search_mods"),
    path("search/licenses/", search.search_licenses, name="search_licenses"),
    path("search/languages/", search.search_languages, name="search_languages"),
    # ---------------------------------------------- File management
    path(
        "mods/remove/<int:file_id>/",
        create.remove_temp_file,
        name="remove_temp_file",
    ),
    # ---------------------------------------------- Explore mods (READ)
    path("explore/mods/", explore.mods, name="explore_mods"),
    path("explore/search/tags/", explore.search_tags, name="explore_search_tags"),
    path("explore/search/dependencies/", explore.search_dependencies, name="explore_search_dependencies"),
    #---------------------------------------------- Mod detail (READ)
    path("mods/<int:mod_id>/", detail.mod_detail, name="mod_detail"),
    path("mods/files/<int:file_id>/download/", detail.download_file, name="mod_file_download"),
    # ---------------------------------------------- Session management
    path("mods/create/cancel/", create.cancel_mod_upload, name="cancel_mod_upload"),
    path("mods/<int:mod_id>/edit/", create.edit_mod, name="mod_edit"),
    # ---------------------------------------------- HTMX endpoints
    path(
        "mods/validate-url/",
        validations.hx_process_url_field,
        name="hx_process_url_field",
    ),
    path(
        "mods/edit/<int:mod_id>/file-manager/",
        validations.hx_toggle_file_manager,
        name="hx_toggle_file_manager",
    ),
    path(
        "mods/edit/<int:mod_id>/file-manager/confirm-disable/",
        validations.hx_file_manager_disable_confirm,
        name="hx_file_manager_disable_confirm",
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
        "mods/set-thumbnail-image/<int:image_id>/",
        validations.hx_set_thumbnail_image,
        name="hx_set_thumbnail_image",
    ),
    path(
        "mods/edit/<int:mod_id>/images/reorder/",
        validations.hx_reorder_images,
        name="hx_reorder_images",
    ),
    path("mods/edit/<int:mod_id>/description/preview/", validations.hx_preview_description, name="hx_preview_description"),
    path("mods/edit/<int:mod_id>/description/image/", validations.hx_upload_description_image, name="hx_upload_description_image"),
]
