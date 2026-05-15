"""
Tests for Edit Payment functionality

Tests the edit_payment_view:
- Staff-only access
- GET renders form with pre-populated data
- POST updates payment fields
- POST does NOT change member expiration or payment.new_expiration_date
- Validation errors (future date, empty receipt, invalid amount)
- Edge cases (deceased member, nonexistent payment)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from members.models import Member, MemberType, Payment, PaymentMethod


@pytest.mark.django_db
@pytest.mark.integration
class TestEditPaymentView:
    """Test edit_payment_view functionality"""

    @pytest.fixture
    def staff_user(self, db):
        return User.objects.create_user(
            username="staffuser", password="testpass", is_staff=True
        )

    @pytest.fixture
    def regular_user(self, db):
        return User.objects.create_user(
            username="regularuser", password="testpass", is_staff=False
        )

    @pytest.fixture
    def staff_client(self, staff_user):
        client = Client()
        client.login(username="staffuser", password="testpass")
        return client

    @pytest.fixture
    def regular_client(self, regular_user):
        client = Client()
        client.login(username="regularuser", password="testpass")
        return client

    @pytest.fixture
    def member_type(self, db):
        return MemberType.objects.create(
            member_type="Regular", member_dues=Decimal("20.00"), num_months=1
        )

    @pytest.fixture
    def payment_method_cash(self, db):
        return PaymentMethod.objects.create(payment_method="Cash")

    @pytest.fixture
    def payment_method_check(self, db):
        return PaymentMethod.objects.create(payment_method="Check")

    @pytest.fixture
    def member(self, db, member_type):
        return Member.objects.create(
            first_name="Eric",
            last_name="Phillips",
            member_type=member_type,
            member_id=42,
            status="active",
            expiration_date=date(2026, 4, 30),
            date_joined=date(2010, 2, 6),
        )

    @pytest.fixture
    def payment(self, db, member, payment_method_cash):
        return Payment.objects.create(
            member=member,
            payment_method=payment_method_cash,
            amount=Decimal("20.00"),
            date=date(2026, 3, 1),
            receipt_number="596477",
            new_expiration_date=date(2026, 3, 31),
        )

    def _url(self, payment_id):
        return f"/payments/edit/{payment_id}/"

    # --- Access control ---

    def test_requires_staff(self, regular_client, payment):
        response = regular_client.get(self._url(payment.pk))
        assert response.status_code == 302
        assert "/admin/login/" in response.url

    def test_staff_can_access(self, staff_client, payment):
        response = staff_client.get(self._url(payment.pk))
        assert response.status_code == 200

    # --- GET rendering ---

    def test_get_displays_member_info(self, staff_client, payment, member):
        response = staff_client.get(self._url(payment.pk))
        content = response.content.decode()
        assert "Eric Phillips" in content
        assert "#42" in content

    def test_get_prepopulates_form(self, staff_client, payment):
        response = staff_client.get(self._url(payment.pk))
        content = response.content.decode()
        assert "2026-03-01" in content
        assert "20.00" in content
        assert "596477" in content

    def test_get_shows_payment_list(self, staff_client, member, payment, payment_method_cash):
        Payment.objects.create(
            member=member,
            payment_method=payment_method_cash,
            amount=Decimal("20.00"),
            date=date(2026, 4, 4),
            receipt_number="596565",
        )
        response = staff_client.get(self._url(payment.pk))
        content = response.content.decode()
        assert "596477" in content
        assert "596565" in content

    def test_get_404_for_nonexistent(self, staff_client):
        response = staff_client.get(self._url(99999))
        assert response.status_code == 404

    # --- POST successful edit ---

    def test_post_updates_date(self, staff_client, payment, payment_method_cash):
        staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-02-15",
            "amount": "20.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        payment.refresh_from_db()
        assert payment.date == date(2026, 2, 15)

    def test_post_updates_amount(self, staff_client, payment, payment_method_cash):
        staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "40.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        payment.refresh_from_db()
        assert payment.amount == Decimal("40.00")

    def test_post_updates_payment_method(self, staff_client, payment, payment_method_check):
        staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "20.00",
            "payment_method": str(payment_method_check.pk),
            "receipt_number": "596477",
        })
        payment.refresh_from_db()
        assert payment.payment_method == payment_method_check

    def test_post_updates_receipt_number(self, staff_client, payment, payment_method_cash):
        staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "20.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "NEW-123",
        })
        payment.refresh_from_db()
        assert payment.receipt_number == "NEW-123"

    def test_post_redirects_to_member_detail(self, staff_client, payment, member, payment_method_cash):
        response = staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "20.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        assert response.status_code == 302
        assert str(member.member_uuid) in response.url

    def test_post_shows_success_message(self, staff_client, payment, payment_method_cash):
        response = staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "20.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        detail_response = staff_client.get(response.url)
        assert "Payment updated" in detail_response.content.decode()

    # --- POST does NOT affect expiration ---

    def test_post_does_not_change_member_expiration(self, staff_client, payment, member, payment_method_cash):
        original_expiration = member.expiration_date
        staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "60.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        member.refresh_from_db()
        assert member.expiration_date == original_expiration

    def test_post_does_not_change_member_expiration_even_when_payment_expiration_edited(
        self, staff_client, payment, member, payment_method_cash
    ):
        original_member_exp = member.expiration_date
        staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "60.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
            "new_expiration_date": "2026-06-30",
        })
        payment.refresh_from_db()
        member.refresh_from_db()
        assert payment.new_expiration_date == date(2026, 6, 30)
        assert member.expiration_date == original_member_exp

    # --- POST validation errors ---

    def test_post_rejects_future_date(self, staff_client, payment, payment_method_cash):
        future = (date.today() + timedelta(days=1)).isoformat()
        response = staff_client.post(self._url(payment.pk), {
            "payment_date": future,
            "amount": "20.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        assert response.status_code == 200
        assert "future" in response.content.decode()

    def test_post_rejects_empty_receipt(self, staff_client, payment, payment_method_cash):
        response = staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "20.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "",
        })
        assert response.status_code == 200
        assert "Receipt number is required" in response.content.decode()

    def test_post_rejects_invalid_amount(self, staff_client, payment, payment_method_cash):
        response = staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "abc",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        assert response.status_code == 200
        assert "Invalid payment amount" in response.content.decode()

    def test_post_rejects_negative_amount(self, staff_client, payment, payment_method_cash):
        response = staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "-5.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "596477",
        })
        assert response.status_code == 200
        assert "greater than zero" in response.content.decode()

    def test_post_rejects_invalid_payment_method(self, staff_client, payment):
        response = staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "20.00",
            "payment_method": "99999",
            "receipt_number": "596477",
        })
        assert response.status_code == 200
        assert "Invalid payment method" in response.content.decode()

    # --- Edge cases ---

    def test_cannot_edit_payment_for_deceased_member(self, staff_client, member, payment):
        member.status = "deceased"
        member.save()
        response = staff_client.get(self._url(payment.pk))
        assert response.status_code == 302

    def test_edit_preserves_member_fk(self, staff_client, payment, member, payment_method_cash):
        staff_client.post(self._url(payment.pk), {
            "payment_date": "2026-03-01",
            "amount": "40.00",
            "payment_method": str(payment_method_cash.pk),
            "receipt_number": "CHANGED",
        })
        payment.refresh_from_db()
        assert payment.member == member
