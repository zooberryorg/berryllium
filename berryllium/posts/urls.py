from django.urls import path

from berryllium.posts import views

urlpatterns = [
    # writing
    path("posts/new/", views.create_draft, name="post_create_draft"),
    path("posts/<int:post_id>/edit/", views.edit, name="post_edit"),
    path("posts/<int:post_id>/edit/thumbnail/", views.thumbnail, name="post_thumbnail"),
    path("posts/<int:post_id>/edit/files/", views.files, name="post_files"),
    path("posts/<int:post_id>/edit/files/<int:file_id>/", views.file_change, name="post_file_change"),
    path("posts/<int:post_id>/edit/image/", views.body_image, name="post_body_image"),
    path("posts/<int:post_id>/edit/preview/", views.preview, name="post_preview"),
    # reading
    path("posts/<int:post_id>/", views.detail, name="post_detail"),
    path("posts/files/<int:file_id>/download/", views.download, name="post_file_download"),
    path("explore/tutorials/", views.explore_tutorials, name="explore_tutorials"),
    path("explore/news/", views.explore_news, name="explore_news"),
    # post settings
    path("settings/posts/", views.settings_posts, name="settings_posts"),
    path("settings/posts/<int:post_id>/", views.settings_posts_change, name="settings_posts_change"),
]
