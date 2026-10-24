from django.urls import path

from berryllium.comments import views

urlpatterns = [
    path("comments/<str:kind>/<int:pk>/", views.more, name="comments_more"),
    path("comments/<str:kind>/<int:pk>/new/", views.create, name="comment_create"),
    path("comments/<str:kind>/<int:pk>/section/", views.section, name="comments_section"),
    path("comments/<str:kind>/<int:pk>/updates/", views.updates, name="comments_updates"),
    path("comments/<str:kind>/<int:pk>/toggle/", views.toggle, name="comments_toggle"),
    path("comments/<int:comment_id>/reply/", views.reply_form, name="comment_reply_form"),
    path("comments/<int:comment_id>/edit/", views.edit, name="comment_edit"),
    path("comments/<int:comment_id>/delete/", views.delete, name="comment_delete"),
    # editor helpers shared by comments and inbox messages
    path("markdown/preview/", views.preview, name="markdown_preview"),
    path("markdown/image/", views.image, name="markdown_image"),
]
