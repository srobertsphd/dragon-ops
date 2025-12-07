"""
Tests for Admin Views

Tests the custom admin view:
- deactivate_expired_members_view()
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from members.models import Member, MemberType, Payment, PaymentMethod


@pytest.mark.django_db
@pytest.mark.integration
class TestDeactivateExpiredMembersView:
    """Test deactivate_expired_members_view admin view"""

    @pytest.fixture
    def user(self, db):
        """Create a staff user for authentication"""
        return User.objects.create_user(
            username="admin",
            password="testpass",
            is_staff=True,
        )

    @pytest.fixture
    def client(self, user):
        """Create authenticated client"""
        client = Client()
        client.login(username="admin", password="testpass")
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

    def test_get_view_displays_eligible_members(self, client, member_type):
        """Test that GET request displays eligible expired members"""
        # Create expired member without payment
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="John",
            last_name="Doe",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        response = client.get("/admin/deactivate-expired-members/")
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()

    def test_get_view_excludes_members_with_payment_after_expiration(
        self, client, member_type, payment_method
    ):
        """Test that members with payment after expiration are excluded"""
        # Create expired member with payment after expiration
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="Jane",
            last_name="Smith",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        # Add payment after expiration
        Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=expired_date + timedelta(days=10),  # After expiration
        )

        response = client.get("/admin/deactivate-expired-members/")
        assert response.status_code == 200
        assert "Jane Smith" not in response.content.decode()

    def test_get_view_excludes_recently_expired_members(self, client, member_type):
        """Test that members expired less than 90 days are excluded"""
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

        response = client.get("/admin/deactivate-expired-members/")
        assert response.status_code == 200
        assert "Recent Expired" not in response.content.decode()

    def test_get_view_excludes_inactive_members(self, client, member_type):
        """Test that inactive members are excluded"""
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

        response = client.get("/admin/deactivate-expired-members/")
        assert response.status_code == 200
        assert "Inactive Member" not in response.content.decode()

    def test_get_view_shows_empty_message_when_no_members(self, client):
        """Test that empty state message is shown when no eligible members"""
        response = client.get("/admin/deactivate-expired-members/")
        assert response.status_code == 200
        assert "No members found" in response.content.decode()

    def test_post_view_deactivates_selected_members(self, client, member_type):
        """Test that POST request deactivates selected members"""
        # Create expired member
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="Bob",
            last_name="Johnson",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
            member_id=42,
        )

        response = client.post(
            "/admin/deactivate-expired-members/",
            {"member_uuids": [str(member.member_uuid)]},
        )

        # Should redirect after POST
        assert response.status_code == 302

        # Verify member was deactivated
        member.refresh_from_db()
        assert member.status == "inactive"
        assert member.member_id is None
        assert member.preferred_member_id == 42  # Should be saved

    def test_post_view_with_no_selection_shows_warning(self, client):
        """Test that POST with no selection shows warning message"""
        response = client.post("/admin/deactivate-expired-members/", {})

        # Should redirect
        assert response.status_code == 302

    def test_post_view_validates_eligibility_before_deactivating(
        self, client, member_type, payment_method
    ):
        """Test that POST validates eligibility even if member was selected"""
        # Create expired member with payment after expiration
        expired_date = date.today() - timedelta(days=95)
        member = Member.objects.create(
            first_name="Protected",
            last_name="Member",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        # Add payment after expiration (should protect member)
        Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal("30.00"),
            date=expired_date + timedelta(days=5),
        )

        response = client.post(
            "/admin/deactivate-expired-members/",
            {"member_uuids": [str(member.member_uuid)]},
        )

        # Should redirect
        assert response.status_code == 302

        # Verify member was NOT deactivated (has payment after expiration)
        member.refresh_from_db()
        assert member.status == "active"

    def test_post_view_deactivates_multiple_members(self, client, member_type):
        """Test that POST can deactivate multiple members at once"""
        # Create multiple expired members
        expired_date = date.today() - timedelta(days=95)
        member1 = Member.objects.create(
            first_name="Member",
            last_name="One",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
            member_id=10,
        )
        member2 = Member.objects.create(
            first_name="Member",
            last_name="Two",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
            member_id=20,
        )

        response = client.post(
            "/admin/deactivate-expired-members/",
            {
                "member_uuids": [
                    str(member1.member_uuid),
                    str(member2.member_uuid),
                ]
            },
        )

        assert response.status_code == 302

        # Verify both were deactivated
        member1.refresh_from_db()
        member2.refresh_from_db()
        assert member1.status == "inactive"
        assert member2.status == "inactive"
        assert member1.member_id is None
        assert member2.member_id is None

    def test_view_requires_staff_authentication(self, db, member_type):
        """Test that non-staff users cannot access the view"""
        # Create non-staff user
        user = User.objects.create_user(
            username="regular",
            password="testpass",
            is_staff=False,
        )
        client = Client()
        client.login(username="regular", password="testpass")

        response = client.get("/admin/deactivate-expired-members/")
        # Should redirect to login or return 403
        assert response.status_code in [302, 403]

    def test_view_requires_authentication(self, db):
        """Test that unauthenticated users cannot access the view"""
        client = Client()
        response = client.get("/admin/deactivate-expired-members/")
        # Should redirect to login
        assert response.status_code == 302
