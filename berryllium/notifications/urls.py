from django.urls import path

from berryllium.notifications import views

urlpatterns = [
    path("notifications/", views.index, name="notifications"),
    path("notifications/menu/", views.menu, name="notifications_menu"),
    path("notifications/badge/", views.badge, name="notifications_badge"),
    path("notifications/read-all/", views.mark_all_read, name="notifications_read_all"),
    path("notifications/<int:notification_id>/", views.open_notification, name="notification_open"),
]
