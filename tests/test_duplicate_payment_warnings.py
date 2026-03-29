"""
Tests for Change #028: Duplicate Payment Detection Warnings

Tests that:
- Duplicate receipt number warnings appear on add_payment confirmation page
- Same member + same date warnings appear on add_payment confirmation page
- No warnings when receipt/date are unique
- Warnings don't block payment processing
- Warnings appear on add_member (reactivation) confirmation page
- Shared partial template is used by both flows
"""

import pytest
from datetime import date
from decimal import Decimal

from django.test import Client
from django.contrib.auth.models import User
from django.template.loader import get_template

from members.models import Member, MemberType, Payment, PaymentMethod


@pytest.mark.django_db
class TestDuplicatePaymentWarnings:
    """Test duplicate detection on the add_payment confirmation page"""

    @pytest.fixture
    def staff_user(self, db):
        return User.objects.create_user(
            username="staffuser", password="testpass", is_staff=True
        )

    @pytest.fixture
    def staff_client(self, staff_user):
        client = Client()
        client.login(username="staffuser", password="testpass")
        return client

    @pytest.fixture
    def member_type(self, db):
        return MemberType.objects.create(
            member_type="Regular", member_dues=Decimal("30.00"), num_months=1
        )

    @pytest.fixture
    def payment_method(self, db):
        return PaymentMethod.objects.create(payment_method="Cash")

    @pytest.fixture
    def member(self, db, member_type):
        return Member.objects.create(
            first_name="John",
            last_name="Doe",
            member_type=member_type,
            status="active",
            expiration_date=date(2026, 3, 31),
            date_joined=date(2020, 1, 1),
        )

    @pytest.fixture
    def existing_payment(self, db, member, payment_method):
        return Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2026, 3, 15),
            receipt_number="RCPT-100",
        )

    def _post_confirm(self, staff_client, member, payment_method, **overrides):
        data = {
            "member_uuid": str(member.member_uuid),
            "amount": "30.00",
            "payment_date": "2026-04-01",
            "payment_method": str(payment_method.pk),
            "receipt_number": "RCPT-NEW",
        }
        data.update(overrides)
        return staff_client.post("/payments/add/?step=confirm", data)

    # --- Receipt warnings ---

    def test_no_receipt_warning_when_unique(
        self, staff_client, member, payment_method, existing_payment
    ):
        resp = self._post_confirm(staff_client, member, payment_method)
        assert resp.status_code == 200
        assert b"Duplicate Receipt Number" not in resp.content

    def test_receipt_warning_shown_when_duplicate(
        self, staff_client, member, payment_method, existing_payment
    ):
        resp = self._post_confirm(
            staff_client, member, payment_method, receipt_number="RCPT-100"
        )
        assert resp.status_code == 200
        assert b"Duplicate Receipt Number" in resp.content
        assert b"RCPT-100" in resp.content
        assert b"John" in resp.content
        assert b"Doe" in resp.content

    def test_receipt_warning_shows_multiple_matches(
        self, staff_client, member, payment_method, existing_payment
    ):
        other_member = Member.objects.create(
            first_name="Jane",
            last_name="Smith",
            member_type=member.member_type,
            status="active",
            expiration_date=date(2026, 5, 31),
            date_joined=date(2021, 1, 1),
        )
        Payment.objects.create(
            member=other_member,
            payment_method=payment_method,
            amount=Decimal("60.00"),
            date=date(2026, 2, 10),
            receipt_number="RCPT-100",
        )
        resp = self._post_confirm(
            staff_client, member, payment_method, receipt_number="RCPT-100"
        )
        content = resp.content.decode()
        assert "John" in content
        assert "Jane" in content

    # --- Date warnings ---

    def test_no_date_warning_when_unique(
        self, staff_client, member, payment_method, existing_payment
    ):
        resp = self._post_confirm(staff_client, member, payment_method)
        assert b"Existing Payment on This Date" not in resp.content

    def test_date_warning_shown_when_same_member_same_date(
        self, staff_client, member, payment_method, existing_payment
    ):
        resp = self._post_confirm(
            staff_client, member, payment_method, payment_date="2026-03-15"
        )
        assert resp.status_code == 200
        assert b"Existing Payment on This Date" in resp.content
        assert b"RCPT-100" in resp.content

    def test_no_date_warning_for_different_member_same_date(
        self, staff_client, member, payment_method, existing_payment
    ):
        other_member = Member.objects.create(
            first_name="Jane",
            last_name="Smith",
            member_type=member.member_type,
            status="active",
            expiration_date=date(2026, 5, 31),
            date_joined=date(2021, 1, 1),
        )
        resp = self._post_confirm(
            staff_client, other_member, payment_method, payment_date="2026-03-15"
        )
        assert b"Existing Payment on This Date" not in resp.content

    # --- Warnings don't block processing ---

    def test_payment_processes_despite_warnings(
        self, staff_client, member, payment_method, existing_payment
    ):
        self._post_confirm(
            staff_client,
            member,
            payment_method,
            receipt_number="RCPT-100",
            payment_date="2026-03-15",
        )
        resp = staff_client.post(
            "/payments/add/?step=process",
            {"confirm": "yes"},
        )
        assert resp.status_code == 302
        assert Payment.objects.filter(receipt_number="RCPT-100").count() == 2


@pytest.mark.django_db
class TestDuplicateWarningsAddMemberFlow:
    """Test duplicate detection on the add_member (reactivation) confirmation page"""

    @pytest.fixture
    def staff_user(self, db):
        return User.objects.create_user(
            username="staffuser", password="testpass", is_staff=True
        )

    @pytest.fixture
    def staff_client(self, staff_user):
        client = Client()
        client.login(username="staffuser", password="testpass")
        return client

    @pytest.fixture
    def member_type(self, db):
        return MemberType.objects.create(
            member_type="Regular", member_dues=Decimal("30.00"), num_months=1
        )

    @pytest.fixture
    def payment_method(self, db):
        return PaymentMethod.objects.create(payment_method="Cash")

    @pytest.fixture
    def inactive_member(self, db, member_type):
        return Member.objects.create(
            first_name="Bob",
            last_name="Jones",
            member_type=member_type,
            status="inactive",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2019, 6, 1),
            date_inactivated=date(2026, 1, 1),
        )

    @pytest.fixture
    def existing_payment(self, db, inactive_member, payment_method):
        return Payment.objects.create(
            member=inactive_member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2026, 3, 10),
            receipt_number="RCPT-200",
        )

    def _setup_reactivation_session(self, staff_client, inactive_member, member_type):
        session = staff_client.session
        session["reactivate_member_uuid"] = str(inactive_member.member_uuid)
        session["member_data"] = {
            "first_name": inactive_member.first_name,
            "last_name": inactive_member.last_name,
            "member_type_id": str(member_type.pk),
        }
        session.save()

    def test_receipt_warning_on_reactivation(
        self, staff_client, inactive_member, member_type, payment_method, existing_payment
    ):
        self._setup_reactivation_session(staff_client, inactive_member, member_type)
        resp = staff_client.post(
            "/add/?step=payment",
            {
                "amount": "30.00",
                "payment_date": "2026-04-01",
                "payment_method": str(payment_method.pk),
                "receipt_number": "RCPT-200",
            },
        )
        assert resp.status_code == 200
        assert b"Duplicate Receipt Number" in resp.content
        assert b"RCPT-200" in resp.content

    def test_date_warning_on_reactivation(
        self, staff_client, inactive_member, member_type, payment_method, existing_payment
    ):
        self._setup_reactivation_session(staff_client, inactive_member, member_type)
        resp = staff_client.post(
            "/add/?step=payment",
            {
                "amount": "30.00",
                "payment_date": "2026-03-10",
                "payment_method": str(payment_method.pk),
                "receipt_number": "RCPT-NEW",
            },
        )
        assert resp.status_code == 200
        assert b"Existing Payment on This Date" in resp.content

    def test_no_warnings_when_clean_on_reactivation(
        self, staff_client, inactive_member, member_type, payment_method, existing_payment
    ):
        self._setup_reactivation_session(staff_client, inactive_member, member_type)
        resp = staff_client.post(
            "/add/?step=payment",
            {
                "amount": "30.00",
                "payment_date": "2026-04-01",
                "payment_method": str(payment_method.pk),
                "receipt_number": "RCPT-CLEAN",
            },
        )
        assert resp.status_code == 200
        assert b"Duplicate Receipt Number" not in resp.content
        assert b"Existing Payment on This Date" not in resp.content


@pytest.mark.django_db
class TestPaymentWarningsPartialTemplate:
    """Test the shared partial template is loadable and renders correctly"""

    def test_partial_template_loads(self):
        template = get_template("members/includes/payment_warnings.html")
        assert template is not None

    def test_partial_renders_empty_when_no_warnings(self):
        template = get_template("members/includes/payment_warnings.html")
        rendered = template.render({})
        stripped = rendered.strip()
        assert stripped == ""

    def test_partial_renders_receipt_warning(self):
        template = get_template("members/includes/payment_warnings.html")
        rendered = template.render(
            {
                "receipt_warnings": [("John", "Doe", date(2026, 3, 15), Decimal("30.00"))],
                "receipt_number": "RCPT-100",
            }
        )
        assert "Duplicate Receipt Number" in rendered
        assert "RCPT-100" in rendered
        assert "John" in rendered

    def test_partial_renders_date_warning(self):
        template = get_template("members/includes/payment_warnings.html")
        rendered = template.render(
            {
                "date_warnings": [("RCPT-100", Decimal("30.00"), "Cash")],
                "warning_member_name": "John Doe",
                "payment_date": date(2026, 3, 15),
            }
        )
        assert "Existing Payment on This Date" in rendered
        assert "John Doe" in rendered
        assert "RCPT-100" in rendered
