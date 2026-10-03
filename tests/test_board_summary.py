import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from reportlab.lib.pagesizes import letter

from members.models import Member, MemberType, Payment, PaymentMethod
from members.reports.board_summary import board_summary_data, generate_board_summary_pdf


def _page_count(pdf):
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf))


def _media_box(pdf):
    match = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
    return float(match.group(1)), float(match.group(2))


def _summary(**overrides):
    data = {
        "report_date": date(2026, 10, 3),
        "start": date(2026, 9, 3),
        "end": date(2026, 10, 3),
        "current_members": 333,
        "rows": [
            {"name": "Regular", "members": 12, "amount": Decimal("240.00")},
            {"name": "Fixed/Income", "members": 8, "amount": Decimal("160.50")},
            {"name": "Life", "members": 0, "amount": Decimal("0.00")},
        ],
        "total_members": 20,
        "total_amount": Decimal("400.50"),
    }
    data.update(overrides)
    return data


@pytest.mark.unit
class TestBoardSummaryPdf:
    def test_pdf_is_one_letter_portrait_page(self):
        pdf = generate_board_summary_pdf(_summary())
        width, height = _media_box(pdf)
        assert abs(width - letter[0]) < 1
        assert abs(height - letter[1]) < 1
        assert height > width
        assert _page_count(pdf) == 1

    def test_pdf_includes_heading_types_and_amounts(self):
        pdf = generate_board_summary_pdf(_summary())
        assert b"Board Summary Report" in pdf
        assert b"October 3, 2026" in pdf
        assert b"September 3, 2026 through October 3, 2026" in pdf
        assert b"REGULAR" in pdf
        assert b"FIXED/INCOME" in pdf
        assert b"LIFE" in pdf
        assert b"TOTAL" in pdf
        assert b"$240.00" in pdf
        assert b"$160.50" in pdf
        assert b"$400.50" in pdf

    def test_many_types_stay_on_one_page(self):
        rows = [
            {"name": f"Type {n}", "members": n, "amount": Decimal("10.00")}
            for n in range(1, 13)
        ]
        pdf = generate_board_summary_pdf(
            _summary(
                rows=rows,
                total_members=78,
                total_amount=Decimal("120.00"),
            )
        )
        assert _page_count(pdf) == 1


@pytest.mark.django_db
@pytest.mark.integration
class TestBoardSummaryData:
    @pytest.fixture
    def payment_method(self, db):
        return PaymentMethod.objects.create(payment_method="Board Cash")

    def _type(self, name):
        return MemberType.objects.create(
            member_type=name,
            member_dues=Decimal("20.00"),
            num_months=1,
        )

    def _member(self, member_type, first, member_id, status="active"):
        return Member.objects.create(
            member_id=member_id,
            first_name=first,
            last_name="Board",
            member_type=member_type,
            status=status,
            expiration_date=date(2026, 12, 31),
            date_joined=date(2020, 1, 1),
        )

    def _pay(self, member, method, amount, paid_on):
        return Payment.objects.create(
            member=member,
            payment_method=method,
            amount=amount,
            date=paid_on,
            receipt_number=f"B{member.member_id or 0}{paid_on.strftime('%m%d')}{amount}",
        )

    def test_groups_dues_and_counts_people_once(self, payment_method):
        regular = self._type("ZZ Board Regular")
        fixed = self._type("ZZ Board Fixed")
        life = self._type("ZZ Board Life")
        active_before = Member.objects.filter(status="active").count()

        payer = self._member(regular, "Ann", 9101)
        self._member(regular, "Bea", 9102)
        self._member(fixed, "Cal", 9103)
        self._member(life, "Dee", 9104, status="inactive")
        inactive_payer = self._member(fixed, "Eve", None, status="inactive")

        start = date(1991, 6, 1)
        end = date(1991, 6, 30)
        self._pay(payer, payment_method, Decimal("20.00"), date(1991, 6, 1))
        self._pay(payer, payment_method, Decimal("15.00"), date(1991, 6, 30))
        self._pay(payer, payment_method, Decimal("100.00"), date(1991, 5, 31))
        self._pay(inactive_payer, payment_method, Decimal("40.00"), date(1991, 6, 15))

        data = board_summary_data(start, end, date(2026, 10, 3))
        by_name = {row["name"]: row for row in data["rows"]}

        assert by_name["ZZ Board Regular"]["members"] == 1
        assert by_name["ZZ Board Regular"]["amount"] == Decimal("35.00")
        assert by_name["ZZ Board Fixed"]["members"] == 1
        assert by_name["ZZ Board Fixed"]["amount"] == Decimal("40.00")
        assert by_name["ZZ Board Life"]["members"] == 0
        assert by_name["ZZ Board Life"]["amount"] == Decimal("0.00")
        assert data["current_members"] == active_before + 3
        assert data["report_date"] == date(2026, 10, 3)


@pytest.mark.django_db
@pytest.mark.integration
class TestBoardSummaryView:
    @pytest.fixture
    def client(self, db):
        User.objects.create_user(username="boardadmin", password="testpass", is_staff=True)
        client = Client()
        client.login(username="boardadmin", password="testpass")
        return client

    def test_page_requires_login(self, db):
        response = Client().get("/reports/board-summary/")
        assert response.status_code == 302

    def test_reports_page_links_to_board_summary(self, client):
        response = client.get("/reports/")
        assert response.status_code == 200
        assert b"Board Summary Report" in response.content
        assert b"/reports/board-summary/" in response.content
        assert b"btn-dark" in response.content

    def test_defaults_are_last_30_days_through_today(self, client):
        today = date.today()
        response = client.get("/reports/board-summary/")
        assert response.status_code == 200
        assert response.context["end_date"] == today
        assert response.context["start_date"] == today - timedelta(days=30)
        assert response.context["summary"] is None
        assert b"Generate PDF" not in response.content

    def test_end_date_before_start_is_rejected(self, client):
        response = client.post(
            "/reports/board-summary/",
            {"action": "preview", "start_date": "2026-05-02", "end_date": "2026-05-01"},
        )
        assert response.status_code == 200
        assert response.context["summary"] is None
        assert b"End date must be on or after the start date." in response.content

    def test_end_date_after_today_is_rejected(self, client):
        tomorrow = date.today() + timedelta(days=1)
        response = client.post(
            "/reports/board-summary/",
            {
                "action": "preview",
                "start_date": date.today().isoformat(),
                "end_date": tomorrow.isoformat(),
            },
        )
        assert response.status_code == 200
        assert response.context["summary"] is None
        assert b"End date cannot be after today." in response.content

    def test_preview_and_pdf_for_a_range_with_no_payments(self, client):
        response = client.post(
            "/reports/board-summary/",
            {
                "action": "preview",
                "start_date": "1991-06-01",
                "end_date": "1991-06-30",
            },
        )
        assert response.status_code == 200
        assert response.context["summary"] is not None
        assert b"board-summary-preview" in response.content
        assert b"Generate PDF" in response.content

        pdf = client.get(
            "/reports/board-summary/",
            {"format": "pdf", "start_date": "1991-06-01", "end_date": "1991-06-30"},
        )
        assert pdf.status_code == 200
        assert pdf["Content-Type"] == "application/pdf"
        assert pdf["Content-Disposition"].startswith("inline;")
        assert _page_count(pdf.content) == 1
        width, height = _media_box(pdf.content)
        assert abs(width - letter[0]) < 1
        assert abs(height - letter[1]) < 1

        download = client.post(
            "/reports/board-summary/",
            {
                "action": "generate",
                "start_date": "1991-06-01",
                "end_date": "1991-06-30",
            },
        )
        assert download.status_code == 200
        assert download["Content-Type"] == "application/pdf"
        assert "attachment;" in download["Content-Disposition"]
        assert b"Board Summary Report" in download.content
