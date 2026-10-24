from django.urls import path

from berryllium.shared import websites

urlpatterns = [
    path("explore/websites/", websites.explore, name="explore_websites"),
    path("websites/<slug:slug>/", websites.profile, name="website_profile"),
]
