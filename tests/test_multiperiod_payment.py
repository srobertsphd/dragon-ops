"""
Tests for Change #029: Multi-Period Payment Discounts

Tests that:
- MemberType discount fields are populated correctly
- calculate_expiration works with duration_months parameter
- Payment view passes duration_options for qualifying member types
- Payment view does NOT pass duration_options for Life/Honorary/500 Club
- Confirm step calculates correct amount and expiration for each duration
- Monthly duration falls back to standard amount-based calculation
"""

import pytest
from datetime import date
from decimal import Decimal

from django.test import Client
from django.contrib.auth.models import User

from members.models import Member, MemberType, Payment, PaymentMethod
from members.services import PaymentService


@pytest.mark.django_db
@pytest.mark.unit
class TestMultiPeriodMemberTypeFields:
    """Test that MemberType discount fields exist and are populated correctly"""

    def test_qualifying_type_has_discount_fields(self, db):
        mt = MemberType.objects.create(
            member_type="TestRegular",
            member_dues=Decimal("30.00"),
            num_months=1,
            six_month_charge=5,
            six_month_duration=6,
            yearly_charge=10,
            yearly_duration=13,
        )
        assert mt.six_month_charge == 5
        assert mt.six_month_duration == 6
        assert mt.yearly_charge == 10
        assert mt.yearly_duration == 13

    def test_non_qualifying_type_has_null_fields(self, db):
        mt = MemberType.objects.create(
            member_type="TestLife",
            member_dues=Decimal("3000.00"),
            num_months=300,
        )
        assert mt.six_month_charge is None
        assert mt.six_month_duration is None
        assert mt.yearly_charge is None
        assert mt.yearly_duration is None


@pytest.mark.django_db
@pytest.mark.unit
class TestCalculateExpirationWithDuration:
    """Test PaymentService.calculate_expiration with duration_months"""

    @pytest.fixture
    def member_type(self, db):
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=Decimal("30.00"),
            num_months=1,
            six_month_charge=5,
            six_month_duration=6,
            yearly_charge=10,
            yearly_duration=13,
        )

    @pytest.fixture
    def member(self, member_type):
        return Member.objects.create(
            first_name="Test",
            last_name="User",
            member_type=member_type,
            status="active",
            expiration_date=date(2026, 3, 31),
            date_joined=date(2020, 1, 1),
        )

    def test_duration_months_6(self, member):
        result = PaymentService.calculate_expiration(
            member, Decimal("150.00"), duration_months=6
        )
        assert result == date(2026, 9, 30)

    def test_duration_months_13(self, member):
        result = PaymentService.calculate_expiration(
            member, Decimal("300.00"), duration_months=13
        )
        assert result == date(2027, 4, 30)

    def test_duration_months_1_same_as_monthly(self, member):
        result = PaymentService.calculate_expiration(
            member, Decimal("30.00"), duration_months=1
        )
        assert result == date(2026, 4, 30)

    def test_override_takes_precedence_over_duration(self, member):
        override = date(2027, 12, 31)
        result = PaymentService.calculate_expiration(
            member, Decimal("150.00"), override_expiration=override, duration_months=6
        )
        assert result == override

    def test_no_duration_falls_back_to_amount(self, member):
        result = PaymentService.calculate_expiration(
            member, Decimal("60.00")
        )
        assert result == date(2026, 5, 31)

    def test_duration_months_crosses_year_boundary(self, member):
        member.expiration_date = date(2026, 11, 30)
        member.save()
        result = PaymentService.calculate_expiration(
            member, Decimal("150.00"), duration_months=6
        )
        assert result == date(2027, 5, 31)


@pytest.mark.django_db
class TestPaymentFormDurationOptions:
    """Test that the payment form shows/hides duration options correctly"""

    @pytest.fixture
    def staff_client(self, db):
        user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        client = Client()
        client.login(username="staff", password="pass")
        return client

    @pytest.fixture
    def payment_method(self, db):
        return PaymentMethod.objects.create(payment_method="Cash")

    @pytest.fixture
    def regular_type(self, db):
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=Decimal("30.00"),
            num_months=1,
            six_month_charge=5,
            six_month_duration=6,
            yearly_charge=10,
            yearly_duration=13,
        )

    @pytest.fixture
    def life_type(self, db):
        return MemberType.objects.create(
            member_type="Life",
            member_dues=Decimal("3000.00"),
            num_months=300,
        )

    @pytest.fixture
    def honorary_type(self, db):
        return MemberType.objects.create(
            member_type="Honorary",
            member_dues=Decimal("0.00"),
            num_months=1,
        )

    @pytest.fixture
    def regular_member(self, regular_type):
        return Member.objects.create(
            first_name="Reg",
            last_name="Member",
            member_type=regular_type,
            status="active",
            expiration_date=date(2026, 3, 31),
            date_joined=date(2020, 1, 1),
            member_id=1,
        )

    @pytest.fixture
    def honorary_member(self, honorary_type):
        return Member.objects.create(
            first_name="Hon",
            last_name="Member",
            member_type=honorary_type,
            status="active",
            expiration_date=date(2026, 3, 31),
            date_joined=date(2020, 1, 1),
            member_id=2,
        )

    def test_duration_radios_shown_for_regular(self, staff_client, regular_member):
        resp = staff_client.get(
            f"/payments/add/?step=form&member={regular_member.member_uuid}"
        )
        assert resp.status_code == 200
        assert b"Payment Duration" in resp.content
        assert b"duration-monthly" in resp.content
        assert b"duration-6month" in resp.content
        assert b"duration-yearly" in resp.content

    def test_duration_radios_hidden_for_honorary(self, staff_client, honorary_member):
        resp = staff_client.get(
            f"/payments/add/?step=form&member={honorary_member.member_uuid}"
        )
        assert resp.status_code == 200
        assert b"Payment Duration" not in resp.content

    def test_life_member_gets_no_payment_page(self, staff_client, life_type):
        life_member = Member.objects.create(
            first_name="Life",
            last_name="Member",
            member_type=life_type,
            status="active",
            expiration_date=date(2099, 12, 31),
            date_joined=date(2010, 1, 1),
            member_id=3,
        )
        resp = staff_client.get(
            f"/payments/add/?step=form&member={life_member.member_uuid}"
        )
        assert resp.status_code == 200
        assert b"No Payment Required" in resp.content


@pytest.mark.django_db
class TestPaymentConfirmDuration:
    """Test confirm step calculates correct amount and expiration per duration"""

    @pytest.fixture
    def staff_client(self, db):
        user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        client = Client()
        client.login(username="staff", password="pass")
        return client

    @pytest.fixture
    def payment_method(self, db):
        return PaymentMethod.objects.create(payment_method="Cash")

    @pytest.fixture
    def member_type(self, db):
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=Decimal("30.00"),
            num_months=1,
            six_month_charge=5,
            six_month_duration=6,
            yearly_charge=10,
            yearly_duration=13,
        )

    @pytest.fixture
    def member(self, member_type):
        return Member.objects.create(
            first_name="Test",
            last_name="User",
            member_type=member_type,
            status="active",
            expiration_date=date(2026, 3, 31),
            date_joined=date(2020, 1, 1),
            member_id=1,
        )

    def _post_confirm(self, staff_client, member, payment_method, duration="monthly"):
        return staff_client.post("/payments/add/?step=confirm", {
            "member_uuid": str(member.member_uuid),
            "amount": "30.00",
            "payment_date": "2026-04-01",
            "payment_method": str(payment_method.pk),
            "receipt_number": "RCPT-DUR",
            "payment_duration": duration,
        })

    def test_monthly_uses_entered_amount(self, staff_client, member, payment_method):
        resp = self._post_confirm(staff_client, member, payment_method, "monthly")
        assert resp.status_code == 200
        assert b"$30" in resp.content

    def test_6month_calculates_5x_dues(self, staff_client, member, payment_method):
        resp = self._post_confirm(staff_client, member, payment_method, "6month")
        assert resp.status_code == 200
        assert b"$150" in resp.content

    def test_yearly_calculates_10x_dues(self, staff_client, member, payment_method):
        resp = self._post_confirm(staff_client, member, payment_method, "yearly")
        assert resp.status_code == 200
        assert b"$300" in resp.content

    def test_6month_expiration_extends_6_months(self, staff_client, member, payment_method):
        resp = self._post_confirm(staff_client, member, payment_method, "6month")
        session_data = staff_client.session["payment_data"]
        assert session_data["new_expiration"] == "2026-09-30"

    def test_yearly_expiration_extends_13_months(self, staff_client, member, payment_method):
        resp = self._post_confirm(staff_client, member, payment_method, "yearly")
        session_data = staff_client.session["payment_data"]
        assert session_data["new_expiration"] == "2027-04-30"

    def test_monthly_expiration_extends_1_month(self, staff_client, member, payment_method):
        resp = self._post_confirm(staff_client, member, payment_method, "monthly")
        session_data = staff_client.session["payment_data"]
        assert session_data["new_expiration"] == "2026-04-30"

    def test_duration_stored_in_session(self, staff_client, member, payment_method):
        self._post_confirm(staff_client, member, payment_method, "yearly")
        session_data = staff_client.session["payment_data"]
        assert session_data["payment_duration"] == "yearly"

    def test_6month_processes_successfully(self, staff_client, member, payment_method):
        self._post_confirm(staff_client, member, payment_method, "6month")
        resp = staff_client.post(
            "/payments/add/?step=process", {"confirm": "yes"}
        )
        assert resp.status_code == 302
        payment = Payment.objects.get(receipt_number="RCPT-DUR")
        assert payment.amount == Decimal("150.00")
        member.refresh_from_db()
        assert member.expiration_date == date(2026, 9, 30)

    def test_yearly_processes_successfully(self, staff_client, member, payment_method):
        self._post_confirm(staff_client, member, payment_method, "yearly")
        resp = staff_client.post(
            "/payments/add/?step=process", {"confirm": "yes"}
        )
        assert resp.status_code == 302
        payment = Payment.objects.get(receipt_number="RCPT-DUR")
        assert payment.amount == Decimal("300.00")
        member.refresh_from_db()
        assert member.expiration_date == date(2027, 4, 30)
