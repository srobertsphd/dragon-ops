"""
Tests for Member Manager methods

Tests the MemberManager class methods:
- get_expired_without_payment()
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from members.models import Member, MemberType, Payment, PaymentMethod


@pytest.mark.django_db
@pytest.mark.unit
class TestMemberManagerGetExpiredWithoutPayment:
    """Test MemberManager.get_expired_without_payment() method"""

    @pytest.fixture
    def member_type(self, db):
        """Create a test member type"""
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=Decimal("30.00"),
            num_months=1,
        )

    @pytest.fixture
    def payment_method(self, db):
        """Create a test payment method"""
        return PaymentMethod.objects.create(payment_method="Cash")

    def test_get_expired_without_payment_finds_eligible_member(self, db, member_type):
        """Test that method finds active member expired 90+ days with no payments"""
        # Create expired member (95 days ago)
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="John",
            last_name="Doe",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        result = Member.objects.get_expired_without_payment()

        assert result.count() == 1
        assert member in result

    def test_get_expired_without_payment_excludes_member_with_payment_after_expiration(
        self, db, member_type, payment_method
    ):
        """Test that method excludes member who paid after expiration"""
        # Create expired member (95 days ago)
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="Jane",
            last_name="Smith",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        # Add payment AFTER expiration date
        Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=expired_date + timedelta(days=10),  # 10 days after expiration
        )

        result = Member.objects.get_expired_without_payment()

        assert result.count() == 0
        assert member not in result

    def test_get_expired_without_payment_includes_member_with_payment_before_expiration(
        self, db, member_type, payment_method
    ):
        """Test that method includes member who only paid before expiration"""
        # Create expired member (95 days ago)
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="Bob",
            last_name="Johnson",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        # Add payment BEFORE expiration date
        Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=expired_date - timedelta(days=10),  # 10 days before expiration
        )

        result = Member.objects.get_expired_without_payment()

        assert result.count() == 1
        assert member in result

    def test_get_expired_without_payment_excludes_inactive_members(
        self, db, member_type
    ):
        """Test that method excludes inactive members"""
        # Create expired inactive member
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="Inactive",
            last_name="Member",
            member_type=member_type,
            status="inactive",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        result = Member.objects.get_expired_without_payment()

        assert result.count() == 0
        assert member not in result

    def test_get_expired_without_payment_excludes_recently_expired_members(
        self, db, member_type
    ):
        """Test that method excludes members expired less than 90 days"""
        # Create member expired only 50 days ago
        expired_date = date.today() - timedelta(days=50)
        member = Member.objects.create(
            first_name="Recent",
            last_name="Expired",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=100),
        )

        result = Member.objects.get_expired_without_payment()

        assert result.count() == 0
        assert member not in result

    def test_get_expired_without_payment_custom_threshold(self, db, member_type):
        """Test that method works with custom days_threshold"""
        # Create member expired 60 days ago
        expired_date = date.today() - timedelta(days=60)
        member = Member.objects.create(
            first_name="Custom",
            last_name="Threshold",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=100),
        )

        # With default threshold (90), should not appear
        result_default = Member.objects.get_expired_without_payment()
        assert member not in result_default

        # With custom threshold (50), should appear
        result_custom = Member.objects.get_expired_without_payment(days_threshold=50)
        assert result_custom.count() == 1
        assert member in result_custom

    def test_get_expired_without_payment_multiple_payments(
        self, db, member_type, payment_method
    ):
        """Test that method correctly handles multiple payments"""
        # Create expired member
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="Multiple",
            last_name="Payments",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        # Add payment before expiration
        Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=expired_date - timedelta(days=20),
        )

        # Add payment after expiration (should exclude member)
        Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=expired_date + timedelta(days=5),
        )

        result = Member.objects.get_expired_without_payment()

        assert result.count() == 0
        assert member not in result

    def test_get_expired_without_payment_member_with_no_payments(self, db, member_type):
        """Test that method includes member with no payments at all"""
        # Create expired member with no payments
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="No",
            last_name="Payments",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        result = Member.objects.get_expired_without_payment()

        assert result.count() == 1
        assert member in result
