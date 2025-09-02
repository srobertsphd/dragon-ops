from django.urls import path
from . import views

app_name = "members"

urlpatterns = [
    # Main pages
    path("", views.landing_view, name="landing"),
    path("search/", views.search_view, name="search"),
    path("<uuid:member_uuid>/", views.member_detail_view, name="member_detail"),
]
