"""
Tests for Reports Views

Tests the reports view:
- deactivate_expired_members_report_view()
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from members.models import Member, MemberType, Payment, PaymentMethod


@pytest.mark.django_db
@pytest.mark.integration
class TestDeactivateExpiredMembersReportView:
    """Test deactivate_expired_members_report_view reports view"""

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
        Member.objects.create(
            first_name="John",
            last_name="Doe",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        response = client.get("/reports/deactivate-expired/")
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

        response = client.get("/reports/deactivate-expired/")
        assert response.status_code == 200
        assert "Jane Smith" not in response.content.decode()

    def test_get_view_excludes_recently_expired_members(self, client, member_type):
        """Test that members expired less than 90 days are excluded"""
        # Create member expired only 50 days ago
        expired_date = date.today() - timedelta(days=50)
        Member.objects.create(
            first_name="Recent",
            last_name="Expired",
            member_type=member_type,
            status="active",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=100),
        )

        response = client.get("/reports/deactivate-expired/")
        assert response.status_code == 200
        assert "Recent Expired" not in response.content.decode()

    def test_get_view_excludes_inactive_members(self, client, member_type):
        """Test that inactive members are excluded"""
        # Create expired inactive member
        expired_date = date.today() - timedelta(days=95)
        Member.objects.create(
            first_name="Inactive",
            last_name="Member",
            member_type=member_type,
            status="inactive",
            expiration_date=expired_date,
            date_joined=date.today() - timedelta(days=200),
        )

        response = client.get("/reports/deactivate-expired/")
        assert response.status_code == 200
        assert "Inactive Member" not in response.content.decode()

    def test_get_view_shows_empty_message_when_no_members(self, client):
        """Test that empty state message is shown when no eligible members"""
        response = client.get("/reports/deactivate-expired/")
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
            "/reports/deactivate-expired/",
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
        response = client.post("/reports/deactivate-expired/", {})

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
            "/reports/deactivate-expired/",
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
            "/reports/deactivate-expired/",
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
        client.force_login(user)

        response = client.get("/reports/deactivate-expired/")
        # Should redirect to login or return 403
        assert response.status_code in [302, 403]

    def test_view_requires_authentication(self, db):
        """Test that unauthenticated users cannot access the view"""
        client = Client()
        response = client.get("/reports/deactivate-expired/")
        # Should redirect to login
        assert response.status_code == 302


@pytest.mark.django_db
@pytest.mark.integration
class TestAddressLabelsView:
    """Test address_labels_view sort order"""

    @pytest.fixture
    def client(self, db):
        User.objects.create_user(
            username="admin",
            password="testpass",
            is_staff=True,
        )
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

    def _make_member(self, member_type, first, last, milestone, address="123 Main St"):
        return Member.objects.create(
            first_name=first,
            last_name=last,
            member_type=member_type,
            status="active",
            expiration_date=date.today() + timedelta(days=90),
            date_joined=date(2010, 1, 1),
            milestone_date=milestone,
            home_address=address,
        )

    def test_preview_orders_by_milestone_day_then_name(self, client, member_type):
        self._make_member(member_type, "Ann", "Adams", date(2010, 6, 28))
        self._make_member(member_type, "Bob", "Baker", date(2020, 6, 3))
        self._make_member(member_type, "Cara", "Clark", date(2015, 6, 12))
        self._make_member(member_type, "Dana", "Davis", date(2018, 6, 12))

        response = client.post(
            "/reports/address-labels/",
            {"month": "6", "action": "preview"},
        )
        assert response.status_code == 200
        names = [
            (m.last_name, m.first_name, m.milestone_date.day)
            for m in response.context["with_address"]
        ]
        assert names == [
            ("Baker", "Bob", 3),
            ("Clark", "Cara", 12),
            ("Davis", "Dana", 12),
            ("Adams", "Ann", 28),
        ]


@pytest.mark.django_db
@pytest.mark.integration
class TestAvailableBadgeNumbersView:
    @pytest.fixture
    def client(self, db):
        User.objects.create_user(
            username="admin",
            password="testpass",
            is_staff=True,
        )
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

    def _make_member(self, member_type, member_id, status="active"):
        return Member.objects.create(
            first_name="Test",
            last_name=f"Id{member_id}",
            member_type=member_type,
            status=status,
            member_id=member_id,
            expiration_date=date.today() + timedelta(days=90),
            date_joined=date(2020, 1, 1),
        )

    def test_shows_next_20_unused_ids(self, client, member_type):
        self._make_member(member_type, 1)
        self._make_member(member_type, 3)

        response = client.get("/reports/available-badge-numbers/")
        assert response.status_code == 200
        numbers = response.context["badge_numbers"]
        assert len(numbers) == 20
        assert numbers[0] == 2
        assert 1 not in numbers
        assert 3 not in numbers
        assert 4 in numbers

        content = response.content.decode()
        assert "Available Badge Numbers" in content
        assert "Badge Number" in content
        assert "Name" in content
        assert "Receipt Number" in content
        assert "Notes" in content
        assert "Page 1 of 1" in content
        assert response.context["report_date"] == date.today()

    def test_inactive_ids_are_available(self, client, member_type):
        self._make_member(member_type, 1, status="inactive")

        response = client.get("/reports/available-badge-numbers/")
        assert response.status_code == 200
        numbers = response.context["badge_numbers"]
        assert numbers[0] == 1

    def test_requires_authentication(self, db):
        client = Client()
        response = client.get("/reports/available-badge-numbers/")
        assert response.status_code == 302

    def test_requires_staff(self, db):
        User.objects.create_user(
            username="regular",
            password="testpass",
            is_staff=False,
        )
        client = Client()
        client.login(username="regular", password="testpass")
        response = client.get("/reports/available-badge-numbers/")
        assert response.status_code in [302, 403]
