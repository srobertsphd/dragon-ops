from django.urls import path
from . import views

app_name = "members"

urlpatterns = [
    # Authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Main pages
    path("", views.landing_view, name="landing"),
    path("search/", views.search_view, name="search"),
    # Member management
    path("add/", views.add_member_view, name="add_member"),
    path("edit/<uuid:member_uuid>/", views.edit_member_view, name="edit_member"),
    path("edit/", views.edit_member_view, name="edit_member"),
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
        "reports/new-members/",
        views.new_member_export_view,
        name="new_member_export",
    ),
    path(
        "reports/milestone-export/",
        views.milestone_export_view,
        name="milestone_export",
    ),
    path(
        "reports/expires-two-months/",
        views.expires_two_months_export_view,
        name="expires_two_months",
    ),
    path(
        "reports/address-labels/",
        views.address_labels_view,
        name="address_labels",
    ),
    path(
        "reports/deactivate-expired/",
        views.deactivate_expired_members_report_view,
        name="deactivate_expired_members",
    ),
    path(
        "reports/backup-download/",
        views.download_backup_view,
        name="download_backup",
    ),
    path(
        "reports/csv-backup/",
        views.csv_backup_export_view,
        name="csv_backup_export",
    ),
    # Payment functionality
    path("payments/add/", views.add_payment_view, name="add_payment"),
    path("payments/edit/<int:payment_id>/", views.edit_payment_view, name="edit_payment"),
    # Member detail (must come after edit routes to avoid conflicts)
    path("<uuid:member_uuid>/", views.member_detail_view, name="member_detail"),
]
