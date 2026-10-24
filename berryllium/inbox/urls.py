from django.urls import path

from berryllium.inbox import views

urlpatterns = [
    path("inbox/", views.index, name="inbox"),
    path("inbox/new/", views.new, name="inbox_new"),
    path("inbox/<int:conversation_id>/", views.conversation, name="inbox_conversation"),
    path("inbox/<int:conversation_id>/delete/", views.delete, name="inbox_delete"),
    path("inbox/<int:conversation_id>/updates/", views.conversation_updates, name="inbox_conversation_updates"),
    path("moderation/inbox/", views.limits, name="moderation_inbox"),
]
