import re
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from django.test import Client
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

from members.models import Member, MemberType

from members.reports.badges import (
    NAME_FONT,
    NAME_SIZE,
    badge_content,
    badge_display_name,
    fitted_font_size,
    generate_badges_pdf,
)


def _member(member_id, first="Jose", last="Martinez"):
    return SimpleNamespace(
        first_name=first,
        last_name=last,
        member_id=member_id,
        date_joined=date(2026, 5, 2),
    )


def _page_count(pdf):
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf))


def _media_box(pdf):
    match = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
    return float(match.group(1)), float(match.group(2))


@pytest.mark.unit
class TestBadgeContent:
    def test_name_is_first_name_and_last_initial(self):
        assert badge_display_name("Jose", "Martinez") == "Jose M."

    def test_name_does_not_include_full_last_name(self):
        content = badge_content("Jose", "Martinez", 226, date(2026, 5, 2))
        assert content["name"] == "Jose M."
        assert "Martinez" not in content["name"]

    def test_empty_last_name_prints_first_name_only(self):
        assert badge_display_name("Jose", "") == "Jose"
        assert badge_display_name("Jose", "   ") == "Jose"

    def test_last_initial_is_uppercased(self):
        assert badge_display_name("Lisa", "rivera") == "Lisa R."

    def test_badge_number_is_member_id_without_padding(self):
        content = badge_content("Thompson", "Smith", 24, date(2026, 5, 1))
        assert content["badge_no"] == "24"

    def test_since_date_is_join_date_without_leading_zeros(self):
        content = badge_content("Jose", "Martinez", 226, date(2026, 5, 2))
        assert content["since"] == "5/2/2026"
        assert content["club"] == "The Alano Club of San Jose"


@pytest.mark.unit
class TestBadgePdf:
    def test_pdf_is_a4(self):
        pdf = generate_badges_pdf([_member(226)])
        width, height = _media_box(pdf)
        assert abs(width - A4[0]) < 1
        assert abs(height - A4[1]) < 1

    def test_ten_badges_fit_on_one_page(self):
        pdf = generate_badges_pdf([_member(n) for n in range(1, 11)])
        assert _page_count(pdf) == 1

    def test_eleventh_badge_starts_a_new_page(self):
        pdf = generate_badges_pdf([_member(n) for n in range(1, 12)])
        assert _page_count(pdf) == 2

    def test_long_name_shrinks_to_the_printable_width(self):
        width = 65 * mm
        short = fitted_font_size("Joe A.", NAME_FONT, NAME_SIZE, width)
        long_name = "Alexandria W."
        long = fitted_font_size(long_name, NAME_FONT, NAME_SIZE, width)
        assert short == NAME_SIZE
        assert long < NAME_SIZE
        assert stringWidth(long_name, NAME_FONT, long) <= width

    def test_badge_labels_are_burgundy(self):
        pdf = generate_badges_pdf([_member(226)])
        assert b".5 0 0 rg" in pdf
        assert b"Jose M." in pdf


@pytest.mark.django_db
@pytest.mark.integration
class TestBadgesView:
    @pytest.fixture
    def client(self, db):
        User.objects.create_user(username="admin", password="testpass", is_staff=True)
        client = Client()
        client.login(username="admin", password="testpass")
        return client

    @pytest.fixture
    def member_type(self, db):
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=Decimal("30.00"),
            num_months=1,
        )

    def _member(self, member_type, first, last, joined, member_id=226, status="active"):
        return Member.objects.create(
            member_id=member_id,
            first_name=first,
            last_name=last,
            member_type=member_type,
            status=status,
            expiration_date=date.today() + timedelta(days=90),
            date_joined=joined,
        )

    def test_page_requires_login(self, db):
        response = Client().get("/reports/badges/")
        assert response.status_code == 302

    def test_reports_page_links_to_badges(self, client):
        response = client.get("/reports/")
        assert response.status_code == 200
        assert b"Print Badges" in response.content
        assert b"/reports/badges/" in response.content

    def test_defaults_are_last_30_days_through_today(self, client):
        today = date.today()
        response = client.get("/reports/badges/")
        assert response.status_code == 200
        assert response.context["end_date"] == today
        assert response.context["start_date"] == today - timedelta(days=30)
        assert b"Generate PDF" not in response.content

    def test_preview_includes_only_new_active_members(self, client, member_type):
        today = date.today()
        self._member(member_type, "Jose", "Martinez", today, member_id=226)
        self._member(member_type, "Old", "Timer", today - timedelta(days=31), member_id=100)
        self._member(
            member_type, "Ina", "Active", today, member_id=101, status="inactive"
        )
        self._member(member_type, "No", "Number", today, member_id=None)

        response = client.post(
            "/reports/badges/",
            {
                "action": "preview",
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
            },
        )
        assert response.status_code == 200
        assert [b["name"] for b in response.context["badges"]] == ["Jose M."]
        assert b"Martinez" not in response.content
        assert b"badge-preview" in response.content
        assert b"format=pdf" in response.content
        assert b"Generate PDF" in response.content

        pdf = client.get(
            "/reports/badges/",
            {
                "format": "pdf",
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
            },
        )
        assert pdf.status_code == 200
        assert pdf["Content-Type"] == "application/pdf"
        assert pdf["Content-Disposition"].startswith("inline;")
        assert b"Jose M." in pdf.content
        assert b"Martinez" not in pdf.content

    def test_preview_orders_by_join_date_then_name(self, client, member_type):
        self._member(member_type, "Zoe", "Young", date(2026, 1, 2), member_id=3)
        self._member(member_type, "Ann", "Young", date(2026, 1, 1), member_id=1)
        self._member(member_type, "Bea", "Adams", date(2026, 1, 2), member_id=2)

        response = client.post(
            "/reports/badges/",
            {
                "action": "preview",
                "start_date": "2026-01-01",
                "end_date": date.today().isoformat(),
            },
        )
        assert [b["name"] for b in response.context["badges"]] == [
            "Ann Y.",
            "Bea A.",
            "Zoe Y.",
        ]

    def test_end_date_before_start_is_rejected(self, client):
        response = client.post(
            "/reports/badges/",
            {"action": "preview", "start_date": "2026-05-02", "end_date": "2026-05-01"},
        )
        assert response.status_code == 200
        assert response.context["badges"] is None
        assert b"End date must be on or after the start date." in response.content

    def test_end_date_after_today_is_rejected(self, client):
        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            "/reports/badges/",
            {
                "action": "preview",
                "start_date": date.today().isoformat(),
                "end_date": tomorrow.isoformat(),
            },
        )
        assert response.status_code == 200
        assert response.context["badges"] is None
        assert b"End date cannot be after today." in response.content

    def test_empty_range_does_not_return_a_pdf(self, client):
        response = client.post(
            "/reports/badges/",
            {
                "action": "generate",
                "start_date": "2020-01-01",
                "end_date": "2020-01-02",
            },
        )
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/html")
        assert b"No new members in that date range." in response.content
        assert b"Generate PDF" not in response.content

    def test_generate_returns_a_pdf(self, client, member_type):
        today = date.today()
        self._member(member_type, "Jose", "Martinez", today, member_id=226)
        response = client.post(
            "/reports/badges/",
            {
                "action": "generate",
                "start_date": (today - timedelta(days=30)).isoformat(),
                "end_date": today.isoformat(),
            },
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "attachment;" in response["Content-Disposition"]
        assert _page_count(response.content) == 1
