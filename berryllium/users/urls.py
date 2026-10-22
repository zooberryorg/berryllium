from django.urls import path, include
from django.contrib.auth.views import LogoutView
from berryllium.users import views

urlpatterns = [
    path("register/", views.MemberRegistration.as_view(), name="register"),
    path("login/", views.MemberLogin.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),
    # profiles
    path("members/<str:username>/", views.member_profile, name="member_profile"),
    path("authors/<int:author_id>/", views.author_profile, name="author_profile"),
]