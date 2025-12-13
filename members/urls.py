from django.urls import path
from . import views

app_name = "members"

urlpatterns = [
    # Main pages
    path("", views.landing_view, name="landing"),
    path("search/", views.search_view, name="search"),
    path("<uuid:member_uuid>/", views.member_detail_view, name="member_detail"),
    # Member management
    path("add/", views.add_member_view, name="add_member"),
    path(
        "reactivate/<uuid:member_uuid>/",
        views.reactivate_member_view,
        name="reactivate_member",
    ),
    # Reports
    path("reports/", views.reports_landing_view, name="reports_landing"),
    path(
        "reports/current-members/",
        views.current_members_report_view,
        name="current_members_report",
    ),
    path(
        "reports/recent-payments/",
        views.recent_payments_report_view,
        name="recent_payments_report",
    ),
    path(
        "reports/newsletter/",
        views.newsletter_export_view,
        name="newsletter_export",
    ),
    path(
        "reports/deactivate-expired/",
        views.deactivate_expired_members_report_view,
        name="deactivate_expired_members",
    ),
    # Payment functionality
    path("payments/add/", views.add_payment_view, name="add_payment"),
]
