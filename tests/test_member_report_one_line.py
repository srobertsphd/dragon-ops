"""Tests for Member Report One Line and amount_to_catch_up."""

import pytest
from datetime import date
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from members.models import Member, MemberType, Payment, PaymentMethod
from members.services import PaymentService


def _make_type(name, dues):
    return MemberType.objects.create(
        member_type=name,
        member_dues=Decimal(dues),
        num_months=1,
    )


def _make_member(member_type, first, last, expiration, member_id=None):
    return Member.objects.create(
        first_name=first,
        last_name=last,
        member_type=member_type,
        status="active",
        expiration_date=expiration,
        date_joined=date(2020, 1, 1),
        member_id=member_id,
    )


@pytest.mark.django_db
@pytest.mark.unit
class TestAmountToCatchUp:
    def test_before_15th_one_month_behind(self):
        member = _make_member(_make_type("Regular", "30.00"), "A", "One", date(2026, 7, 31))
        assert PaymentService.amount_to_catch_up(member, date(2026, 8, 1)) == Decimal("30.00")

    def test_before_15th_already_current_is_blank(self):
        member = _make_member(_make_type("Regular", "30.00"), "A", "One", date(2026, 8, 31))
        assert PaymentService.amount_to_catch_up(member, date(2026, 8, 1)) is None

    def test_on_15th_current_month_owes_next(self):
        member = _make_member(_make_type("Regular", "30.00"), "A", "One", date(2026, 8, 31))
        assert PaymentService.amount_to_catch_up(member, date(2026, 8, 15)) == Decimal("30.00")

    def test_on_15th_three_months_behind(self):
        member = _make_member(_make_type("Regular", "30.00"), "A", "One", date(2026, 5, 31))
        assert PaymentService.amount_to_catch_up(member, date(2026, 8, 15)) == Decimal("120.00")

    def test_uses_member_type_dues(self):
        member = _make_member(_make_type("Couple", "40.00"), "A", "One", date(2026, 7, 31))
        assert PaymentService.amount_to_catch_up(member, date(2026, 8, 1)) == Decimal("40.00")

    def test_skips_life_honorary_and_500_club(self):
        as_of = date(2026, 8, 15)
        expired = date(2026, 5, 31)
        for name, dues in (("Life", "3000.00"), ("Honorary", "0.00"), ("500 Club", "500.00")):
            member = _make_member(_make_type(name, dues), "A", name.replace(" ", ""), expired)
            assert PaymentService.amount_to_catch_up(member, as_of) is None


@pytest.mark.django_db
@pytest.mark.integration
class TestMemberReportOneLineView:
    @pytest.fixture
    def client(self, db):
        User.objects.create_user(username="admin", password="testpass", is_staff=True)
        client = Client()
        client.login(username="admin", password="testpass")
        return client

    def test_default_sort_is_id_and_shows_last_payment_only(self, client):
        member_type = _make_type("Regular", "30.00")
        method = PaymentMethod.objects.create(payment_method="Cash")
        member = _make_member(member_type, "Ann", "Adams", date(2026, 8, 31), member_id=2)
        Payment.objects.create(
            member=member, payment_method=method, amount=Decimal("30.00"),
            date=date(2026, 6, 1), receipt_number="OLD",
        )
        Payment.objects.create(
            member=member, payment_method=method, amount=Decimal("30.00"),
            date=date(2026, 7, 1), receipt_number="NEW",
        )

        response = client.get("/reports/member-report-one-line/")
        assert response.status_code == 200
        assert response.context["current_sort"] == "id"
        row = response.context["members"][0]
        assert len(row["payments"]) == 1
        assert row["payments"][0].receipt_number == "NEW"
        content = response.content.decode()
        assert "NEW" in content
        assert "OLD" not in content
        assert "Amount Due" in content
        assert "Date Joined" not in content
