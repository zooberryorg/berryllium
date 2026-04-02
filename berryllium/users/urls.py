from django.urls import path, include
from berryllium.users import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
]