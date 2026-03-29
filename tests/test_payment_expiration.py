"""
Tests for Change #027: Payment Expiration Tracking.

Covers:
- new_expiration_date field on Payment model
- process_payment() stores the value
- backfill management command
- CSV backup export includes the field
"""

import pytest
from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command

from members.models import Member, MemberType, Payment, PaymentMethod
from members.services import PaymentService
from members.reports.csv_backup import generate_payments_csv_backup, CSV_EXPORT_SCHEMA


@pytest.fixture
def member_type(db):
    return MemberType.objects.create(
        member_type="Regular", member_dues=Decimal("30.00"), num_months=1
    )


@pytest.fixture
def life_type(db):
    return MemberType.objects.create(
        member_type="Life", member_dues=Decimal("0.00"), num_months=0
    )


@pytest.fixture
def payment_method(db):
    return PaymentMethod.objects.create(payment_method="Cash")


@pytest.fixture
def active_member(db, member_type):
    return Member.objects.create(
        first_name="Test",
        last_name="Active",
        member_type=member_type,
        status="active",
        expiration_date=date(2026, 3, 31),
        date_joined=date(2020, 1, 1),
    )


@pytest.mark.django_db
class TestPaymentExpirationField:
    def test_field_exists_and_nullable(self, active_member, payment_method):
        payment = Payment.objects.create(
            member=active_member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2026, 3, 1),
        )
        assert payment.new_expiration_date is None

    def test_field_accepts_date(self, active_member, payment_method):
        payment = Payment.objects.create(
            member=active_member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2026, 3, 1),
            new_expiration_date=date(2026, 4, 30),
        )
        payment.refresh_from_db()
        assert payment.new_expiration_date == date(2026, 4, 30)


@pytest.mark.django_db
class TestProcessPaymentStoresExpiration:
    def test_process_payment_sets_new_expiration_date(
        self, active_member, payment_method
    ):
        payment_data = {
            "payment_method_id": str(payment_method.pk),
            "amount": "30.00",
            "payment_date": "2026-04-01",
            "receipt_number": "R100",
            "new_expiration": "2026-04-30",
        }
        payment, _ = PaymentService.process_payment(active_member, payment_data)
        payment.refresh_from_db()
        assert payment.new_expiration_date == date(2026, 4, 30)

    def test_process_payment_with_override_expiration(
        self, active_member, payment_method
    ):
        payment_data = {
            "payment_method_id": str(payment_method.pk),
            "amount": "30.00",
            "payment_date": "2026-04-01",
            "receipt_number": "R101",
            "new_expiration": "2026-12-31",
        }
        payment, _ = PaymentService.process_payment(active_member, payment_data)
        payment.refresh_from_db()
        assert payment.new_expiration_date == date(2026, 12, 31)


@pytest.mark.django_db
class TestBackfillCommand:
    def test_backfills_most_recent_payment(
        self, active_member, payment_method
    ):
        old = Payment.objects.create(
            member=active_member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2026, 1, 15),
        )
        recent = Payment.objects.create(
            member=active_member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2026, 3, 15),
        )
        call_command("backfill_payment_expiration")
        old.refresh_from_db()
        recent.refresh_from_db()
        assert recent.new_expiration_date == active_member.expiration_date
        assert old.new_expiration_date is None

    def test_skips_life_members(self, life_type, payment_method, db):
        life_member = Member.objects.create(
            first_name="Life",
            last_name="Member",
            member_type=life_type,
            status="active",
            expiration_date=date(2099, 12, 31),
            date_joined=date(2020, 1, 1),
        )
        Payment.objects.create(
            member=life_member,
            payment_method=payment_method,
            amount=Decimal("0.00"),
            date=date(2026, 1, 1),
        )
        call_command("backfill_payment_expiration")
        p = life_member.payments.first()
        assert p.new_expiration_date is None

    def test_skips_inactive_members(self, member_type, payment_method, db):
        inactive = Member.objects.create(
            first_name="Old",
            last_name="Member",
            member_type=member_type,
            status="inactive",
            expiration_date=date(2025, 6, 30),
            date_joined=date(2020, 1, 1),
        )
        Payment.objects.create(
            member=inactive,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2025, 5, 1),
        )
        call_command("backfill_payment_expiration")
        p = inactive.payments.first()
        assert p.new_expiration_date is None


@pytest.mark.django_db
class TestCSVExportIncludesField:
    def test_schema_has_new_expiration_date(self):
        payments_schema = CSV_EXPORT_SCHEMA[3]
        col_names = [c[0] for c in payments_schema["columns"]]
        assert "new_expiration_date" in col_names

    def test_csv_output_includes_value(self, active_member, payment_method):
        Payment.objects.create(
            member=active_member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=date(2026, 3, 1),
            new_expiration_date=date(2026, 4, 30),
        )
        csv_text = generate_payments_csv_backup()
        assert "2026-04-30" in csv_text
