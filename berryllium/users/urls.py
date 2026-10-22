from django.urls import path, include
from django.contrib.auth.views import LogoutView
from berryllium.users import directory, settings_views, views

urlpatterns = [
    path("register/", views.MemberRegistration.as_view(), name="register"),
    path("login/", views.MemberLogin.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),
    # control panel
    path("settings/", settings_views.settings_home, name="settings_home"),
    path("settings/profile/", settings_views.settings_profile, name="settings_profile"),
    path("settings/preferences/", settings_views.settings_preferences, name="settings_preferences"),
    path("settings/account/", settings_views.settings_account, name="settings_account"),
    path("settings/mods/", settings_views.settings_mods, name="settings_mods"),
    path("settings/mods/bulk/", settings_views.settings_mods_bulk, name="settings_mods_bulk"),
    # explore modders
    path("explore/modders/", directory.modders, name="explore_modders"),
    # profiles
    path("members/<str:username>/", views.member_profile, name="member_profile"),
    path("authors/<int:author_id>/", views.author_profile, name="author_profile"),
]