from django.urls import path
from berryllium.organizations import views

urlpatterns = [
    path("orgs/<slug:slug>/", views.profile, name="organization_profile"),
    path("orgs/<slug:slug>/join/", views.join, name="organization_join"),
    path("orgs/<slug:slug>/leave/", views.leave, name="organization_leave"),
    path("orgs/<slug:slug>/manage/", views.manage_page, name="organization_manage_page"),
    path("orgs/<slug:slug>/manage/members/", views.manage_members, name="organization_manage_members"),
    path("orgs/<slug:slug>/manage/inbox/", views.org_inbox, name="organization_inbox"),
    path("orgs/<slug:slug>/manage/inbox/<int:conversation_id>/", views.org_conversation, name="organization_conversation"),
    path("settings/organizations/", views.my_organizations, name="settings_organizations"),
]