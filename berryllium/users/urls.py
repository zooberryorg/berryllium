from django.urls import path, include
from berryllium.users import views

urlpatterns = [
    path("register/", views.MemberRegistration.as_view(), name="register"),
    path("login/", views.MemberLogin.as_view(), name="login"),
]