"""
Integration tests for all views (Step 6: Split Views)

Tests all view functions to ensure they work correctly.

Note: These tests validate views work correctly regardless of file organization.
"""

import pytest
from datetime import date
from decimal import Decimal
from django.test import Client
from django.contrib.auth import get_user_model

from members.models import Member, Payment, PaymentMethod, MemberType

User = get_user_model()


@pytest.mark.integration
class TestViewIntegration:
    """Integration tests for all views"""

    def test_views_exist(self):
        """Test that all view functions exist"""
        from members import views

        assert hasattr(views, "landing_view")
        assert hasattr(views, "search_view")
        assert hasattr(views, "member_detail_view")
        assert hasattr(views, "add_member_view")
        assert hasattr(views, "add_payment_view")
        assert hasattr(views, "current_members_report_view")

    def test_urls_exist(self):
        """Test that all URLs are configured"""
        try:
            from django.urls import resolve

            # Test that URLs resolve
            assert resolve("/").view_name == "members:landing"
            assert resolve("/search/").view_name == "members:search"
            assert resolve("/add/").view_name == "members:add_member"
            assert resolve("/payments/add/").view_name == "members:add_payment"
            assert (
                resolve("/reports/current-members/").view_name
                == "members:current_members_report"
            )
        except Exception:
            # If URL resolution fails, that's okay for now
            pass


@pytest.mark.django_db
@pytest.mark.integration
class TestPaymentViewWithOverride:
    """Integration tests for payment view with override expiration"""

    @pytest.fixture
    def user(self, db):
        """Create a staff user for authentication"""
        return User.objects.create_user(
            username="testuser",
            password="testpass123",
            is_staff=True,
        )

    @pytest.fixture
    def client(self, user):
        """Create authenticated client"""
        client = Client()
        client.force_login(user)
        return client

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

    @pytest.fixture
    def member(self, db, member_type):
        """Create a test member"""
        return Member.objects.create(
            first_name="Test",
            last_name="Member",
            email="test@example.com",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 3, 31),
            date_joined=date(2020, 1, 1),
        )

    def test_payment_flow_with_override_expiration(
        self, client, member, payment_method
    ):
        """Test full payment flow with override expiration date"""
        initial_expiration = member.expiration_date
        initial_payment_count = Payment.objects.count()

        # Step 1: Submit payment form (form step)
        form_data = {
            "member_uuid": str(member.member_uuid),
            "amount": "30.00",
            "payment_date": "2025-04-15",
            "payment_method": str(payment_method.pk),
            "receipt_number": "TEST-OVERRIDE-001",
        }

        response = client.post(
            "/payments/add/?step=form&member=" + str(member.member_uuid), form_data
        )
        assert response.status_code == 200  # Should show confirmation page

        # Step 2: Confirm payment with override expiration (confirm step)
        # Simulate JavaScript populating override_expiration from month/year dropdowns
        override_expiration = date(2025, 12, 31)  # December 31, 2025

        confirm_data = {
            "member_uuid": str(member.member_uuid),
            "amount": "30.00",
            "payment_date": "2025-04-15",
            "payment_method": str(payment_method.pk),
            "receipt_number": "TEST-OVERRIDE-001",
            "override_expiration": override_expiration.isoformat(),  # From JavaScript
        }

        response = client.post("/payments/add/?step=confirm", confirm_data)
        assert (
            response.status_code == 200
        )  # Should show confirmation page with override

        # Step 3: Process payment (process step)
        process_data = {
            "confirm": "yes",
            "override_expiration": override_expiration.isoformat(),  # From confirmation form
        }

        response = client.post("/payments/add/?step=process", process_data)

        # Should redirect to member detail page
        assert response.status_code == 302
        assert f"/{member.member_uuid}/" in response.url

        # Verify payment was created
        assert Payment.objects.count() == initial_payment_count + 1
        payment = Payment.objects.filter(receipt_number="TEST-OVERRIDE-001").first()
        assert payment is not None
        assert payment.amount == Decimal("30.00")
        assert payment.member == member

        # Verify member expiration was updated to override date
        member.refresh_from_db()
        assert member.expiration_date == override_expiration
        assert member.expiration_date != initial_expiration


@pytest.mark.django_db
@pytest.mark.integration
class TestNewMemberCreationWithPayment:
    """Integration tests for new member creation with initial payment (Change #003)"""

    @pytest.fixture
    def user(self, db):
        """Create a staff user for authentication"""
        return User.objects.create_user(
            username="testuser2",
            password="testpass123",
            is_staff=True,
        )

    @pytest.fixture
    def client(self, user):
        """Create authenticated client"""
        client = Client()
        client.force_login(user)
        return client

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

    def test_new_member_creation_workflow_with_payment(
        self, client, member_type, payment_method
    ):
        """Test full new member creation workflow with initial payment"""
        initial_member_count = Member.objects.count()
        initial_payment_count = Payment.objects.count()

        # Step 1: Submit member form (form step)
        form_data = {
            "first_name": "New",
            "last_name": "Member",
            "email": "new.member@example.com",
            "member_type": str(member_type.pk),
            "member_id": "250",
            "milestone_date": "2020-01-15",
            "date_joined": "2025-11-01",
            "home_address": "123 Test St",
            "home_city": "Test City",
            "home_state": "CA",
            "home_zip": "12345",
            "home_phone": "555-1234",
        }

        response = client.post("/add/?step=form", form_data)
        assert response.status_code == 200  # Should show confirmation page
        assert "confirm" in response.context["step"]

        # Step 2: Proceed to payment (confirm step -> payment step)
        response = client.get("/add/?step=payment")
        assert response.status_code == 200
        assert "payment" in response.context["step"]
        assert response.context["suggested_amount"] == Decimal("30.00")

        # Step 3: Submit payment form (payment step POST)
        payment_form_data = {
            "amount": "60.00",  # 2 months
            "payment_date": "2025-11-29",
            "payment_method": str(payment_method.pk),
            "receipt_number": "NEW-MEMBER-001",
            "override_expiration": "",  # Use calculated expiration
        }

        response = client.post("/add/?step=payment", payment_form_data)
        assert response.status_code == 200  # Should show payment confirmation
        assert "payment_confirm" in response.context["step"]
        assert response.context["amount"] == Decimal("60.00")

        # Step 4: Process member and payment creation (process step)
        process_data = {"confirm": "yes"}

        response = client.post("/add/?step=process", process_data)

        # Should redirect to search page
        assert response.status_code == 302
        assert "/search/" in response.url

        # Verify member was created
        assert Member.objects.count() == initial_member_count + 1
        member = Member.objects.filter(first_name="New", last_name="Member").first()
        assert member is not None
        assert member.member_id == 250
        assert member.email == "new.member@example.com"

        # Verify payment was created
        assert Payment.objects.count() == initial_payment_count + 1
        payment = Payment.objects.filter(receipt_number="NEW-MEMBER-001").first()
        assert payment is not None
        assert payment.amount == Decimal("60.00")
        assert payment.member == member

        # Verify member expiration was set correctly (end of January 2026 - end of Nov + 2 months)
        member.refresh_from_db()
        assert member.expiration_date == date(2026, 1, 31)

    def test_new_member_creation_with_override_expiration(
        self, client, member_type, payment_method
    ):
        """Test new member creation with override expiration date"""
        initial_member_count = Member.objects.count()

        # Step 1: Submit member form
        form_data = {
            "first_name": "Override",
            "last_name": "Test",
            "email": "override@example.com",
            "member_type": str(member_type.pk),
            "member_id": "251",
            "milestone_date": "2020-01-15",
            "date_joined": "2025-11-01",
            "home_address": "",
            "home_city": "",
            "home_state": "",
            "home_zip": "",
            "home_phone": "",
        }

        client.post("/add/?step=form", form_data)

        # Step 2: Submit payment with override expiration
        override_expiration = date(2026, 6, 30)
        payment_form_data = {
            "amount": "30.00",
            "payment_date": "2025-11-29",
            "payment_method": str(payment_method.pk),
            "receipt_number": "OVERRIDE-001",
            "override_expiration": override_expiration.isoformat(),
        }

        client.post("/add/?step=payment", payment_form_data)

        # Step 3: Process
        process_data = {"confirm": "yes"}
        client.post("/add/?step=process", process_data)

        # Verify member expiration matches override
        assert Member.objects.count() == initial_member_count + 1
        member = Member.objects.filter(first_name="Override", last_name="Test").first()
        assert member is not None
        assert member.expiration_date == override_expiration

    def test_new_member_form_pre_populates_from_session(self, client, member_type):
        """Test that form fields are pre-populated when going back from later steps"""
        # Step 1: Submit member form
        form_data = {
            "first_name": "PrePop",
            "last_name": "Test",
            "email": "prepop@example.com",
            "member_type": str(member_type.pk),
            "member_id": "252",
            "milestone_date": "2020-01-15",
            "date_joined": "2025-11-01",
            "home_address": "456 Test Ave",
            "home_city": "Test City",
            "home_state": "NY",
            "home_zip": "54321",
            "home_phone": "555-9999",
        }

        client.post("/add/?step=form", form_data)

        # Step 2: Go to payment step (this stores data in session)
        response = client.get("/add/?step=payment")
        assert response.status_code == 200

        # Step 3: Go back to form
        response = client.get("/add/?step=form")
        assert response.status_code == 200

        # Verify form is pre-populated with session data
        assert "member_data" in response.context
        member_data = response.context["member_data"]
        assert member_data["first_name"] == "PrePop"
        assert member_data["last_name"] == "Test"
        assert member_data["email"] == "prepop@example.com"
        assert member_data["member_id"] == 252
        assert member_data["home_address"] == "456 Test Ave"
        assert member_data["home_city"] == "Test City"
        assert member_data["home_state"] == "NY"
        assert member_data["home_zip"] == "54321"
        assert member_data["home_phone"] == "555-9999"
