from django.urls import path

from berryllium.posts import views

urlpatterns = [
    # writing
    path("articles/new/", views.create_draft, name="post_create_draft"),
    path("articles/<int:post_id>/edit/", views.edit, name="post_edit"),
    path("articles/<int:post_id>/edit/thumbnail/", views.thumbnail, name="post_thumbnail"),
    path("articles/<int:post_id>/edit/files/", views.files, name="post_files"),
    path("articles/<int:post_id>/edit/files/<int:file_id>/", views.file_change, name="post_file_change"),
    path("articles/<int:post_id>/edit/image/", views.body_image, name="post_body_image"),
    path("articles/<int:post_id>/edit/preview/", views.preview, name="post_preview"),
    # reading
    path("articles/<int:post_id>/", views.detail, name="post_detail"),
    path("articles/files/<int:file_id>/download/", views.download, name="post_file_download"),
    path("explore/tutorials/", views.explore_tutorials, name="explore_tutorials"),
    path("explore/news/", views.explore_news, name="explore_news"),
    path("explore/search/article-tags/", views.search_article_tags, name="explore_search_article_tags"),
    # Control Panel > My articles
    path("settings/articles/", views.settings_posts, name="settings_posts"),
    path("settings/articles/<int:post_id>/", views.settings_posts_change, name="settings_posts_change"),
]
