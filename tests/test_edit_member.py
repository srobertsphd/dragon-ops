"""
Tests for Edit Member functionality

Tests the edit_member_view:
- Search mode (GET/POST with query)
- Edit mode (GET/POST with member_uuid)
- Staff-only access
- Active member restriction
- Field validation
- Member ID uniqueness
- Expiration date end-of-month enforcement
"""

import pytest
from datetime import date
from decimal import Decimal
from django.test import Client
from django.contrib.auth.models import User

from members.models import Member, MemberType


@pytest.mark.django_db
@pytest.mark.integration
class TestEditMemberView:
    """Test edit_member_view functionality"""

    @pytest.fixture
    def staff_user(self, db):
        """Create a staff user"""
        return User.objects.create_user(
            username="staffuser",
            password="testpass",
            is_staff=True,
        )

    @pytest.fixture
    def regular_user(self, db):
        """Create a regular (non-staff) user"""
        return User.objects.create_user(
            username="regularuser",
            password="testpass",
            is_staff=False,
        )

    @pytest.fixture
    def staff_client(self, staff_user):
        """Create authenticated staff client"""
        client = Client()
        client.login(username="staffuser", password="testpass")
        return client

    @pytest.fixture
    def regular_client(self, regular_user):
        """Create authenticated regular client"""
        client = Client()
        client.login(username="regularuser", password="testpass")
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
    def active_member(self, db, member_type):
        """Create an active member for editing"""
        return Member.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            member_type=member_type,
            member_id=100,
            status="active",
            expiration_date=date(2025, 12, 31),
            milestone_date=date(2020, 1, 1),
            date_joined=date(2020, 1, 1),
            home_address="123 Main St",
            home_city="San Jose",
            home_state="CA",
            home_zip="95110",
            home_phone="(408) 555-1234",
        )

    @pytest.fixture
    def inactive_member(self, db, member_type):
        """Create an inactive member"""
        return Member.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            member_type=member_type,
            member_id=None,
            status="inactive",
            expiration_date=date(2024, 1, 31),
            date_joined=date(2020, 1, 1),
        )

    # Search Mode Tests
    def test_search_mode_get_displays_form(self, staff_client):
        """Test that GET request to edit/ shows search form"""
        response = staff_client.get("/members/edit/")
        assert response.status_code == 200
        assert "Edit Member - Search" in response.content.decode()
        assert "Enter member name or ID" in response.content.decode()

    def test_search_mode_requires_staff(self, regular_client):
        """Test that non-staff users cannot access edit page"""
        response = regular_client.get("/members/edit/")
        assert response.status_code == 403  # Forbidden

    def test_search_by_member_id(self, staff_client, active_member):
        """Test searching by member ID"""
        response = staff_client.get("/members/edit/?q=100")
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()
        assert "#100" in response.content.decode()

    def test_search_by_first_name(self, staff_client, active_member):
        """Test searching by first name"""
        response = staff_client.get("/members/edit/?q=John")
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()

    def test_search_by_last_name(self, staff_client, active_member):
        """Test searching by last name"""
        response = staff_client.get("/members/edit/?q=Doe")
        assert response.status_code == 200
        assert "John Doe" in response.content.decode()

    def test_search_only_shows_active_members(
        self, staff_client, active_member, inactive_member
    ):
        """Test that search only returns active members"""
        response = staff_client.get("/members/edit/?q=Jane")
        assert response.status_code == 200
        assert "Jane Smith" not in response.content.decode()

    def test_search_no_results(self, staff_client):
        """Test search with no matching results"""
        response = staff_client.get("/members/edit/?q=Nonexistent")
        assert response.status_code == 200
        assert "No active members found" in response.content.decode()

    # Edit Mode Tests
    def test_edit_mode_get_displays_form(self, staff_client, active_member):
        """Test that GET request to edit/<uuid>/ shows edit form"""
        response = staff_client.get(f"/members/edit/{active_member.member_uuid}/")
        assert response.status_code == 200
        assert "Edit Member" in response.content.decode()
        assert "John" in response.content.decode()
        assert "Doe" in response.content.decode()
        assert "john@example.com" in response.content.decode()

    def test_edit_mode_requires_staff(self, regular_client, active_member):
        """Test that non-staff users cannot access edit form"""
        response = regular_client.get(f"/members/edit/{active_member.member_uuid}/")
        assert response.status_code == 403  # Forbidden

    def test_edit_mode_requires_active_member(
        self, staff_client, inactive_member
    ):
        """Test that inactive members cannot be edited"""
        response = staff_client.get(f"/members/edit/{inactive_member.member_uuid}/")
        assert response.status_code == 302  # Redirect
        assert "/members/edit/" in response.url

    def test_edit_mode_post_updates_member(self, staff_client, active_member, member_type):
        """Test that POST request updates member successfully"""
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Updated",
                "email": "updated@example.com",
                "member_type": member_type.pk,
                "member_id": "100",
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
                "home_address": "456 New St",
                "home_city": "San Francisco",
                "home_state": "CA",
                "home_zip": "94102",
                "home_phone": "(415) 555-5678",
            },
        )
        assert response.status_code == 302  # Redirect to member_detail
        assert str(active_member.member_uuid) in response.url

        # Verify member was updated
        active_member.refresh_from_db()
        assert active_member.last_name == "Updated"
        assert active_member.email == "updated@example.com"
        assert active_member.home_city == "San Francisco"
        assert active_member.home_zip == "94102"

    def test_edit_mode_validates_required_fields(self, staff_client, active_member, member_type):
        """Test that required fields are validated"""
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "",
                "last_name": "",
                "member_type": member_type.pk,
                "member_id": "100",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 200  # Form with errors
        assert "Required fields are missing" in response.content.decode()

    def test_edit_mode_validates_member_id_range(self, staff_client, active_member, member_type):
        """Test that member ID must be between 1-999"""
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": member_type.pk,
                "member_id": "1000",  # Out of range
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 200
        assert "Member ID must be between 1 and 999" in response.content.decode()

    def test_edit_mode_validates_member_id_uniqueness(
        self, staff_client, active_member, member_type
    ):
        """Test that member ID must be unique (excluding current member)"""
        # Create another member with ID 200
        Member.objects.create(
            first_name="Other",
            last_name="Member",
            member_type=member_type,
            member_id=200,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        # Try to change active_member's ID to 200
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": member_type.pk,
                "member_id": "200",  # Already taken
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 200
        assert "already in use" in response.content.decode()

    def test_edit_mode_allows_same_member_id(self, staff_client, active_member, member_type):
        """Test that member can keep their own member ID"""
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": member_type.pk,
                "member_id": "100",  # Same ID
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 302  # Success

    def test_edit_mode_validates_email_format(self, staff_client, active_member, member_type):
        """Test that email format is validated"""
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "invalid-email",
                "member_type": member_type.pk,
                "member_id": "100",
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 200
        assert "valid email address" in response.content.decode()

    def test_edit_mode_validates_date_joined_not_future(
        self, staff_client, active_member, member_type
    ):
        """Test that date joined cannot be in the future"""
        from datetime import timedelta
        future_date = (date.today() + timedelta(days=1)).isoformat()

        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": member_type.pk,
                "member_id": "100",
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": future_date,
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 200
        assert "Date joined cannot be in the future" in response.content.decode()

    def test_edit_mode_validates_milestone_date_not_future(
        self, staff_client, active_member, member_type
    ):
        """Test that milestone date cannot be in the future"""
        from datetime import timedelta
        future_date = (date.today() + timedelta(days=1)).isoformat()

        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": member_type.pk,
                "member_id": "100",
                "milestone_date": future_date,
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 200
        assert "Milestone date cannot be in the future" in response.content.decode()

    def test_edit_mode_enforces_expiration_end_of_month(
        self, staff_client, active_member, member_type
    ):
        """Test that expiration date is adjusted to end of month"""
        # Submit with override_expiration set to middle of month
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": member_type.pk,
                "member_id": "100",
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-15",  # Middle of month
            },
        )
        assert response.status_code == 302  # Success

        # Verify expiration was adjusted to end of month
        active_member.refresh_from_db()
        assert active_member.expiration_date.day == 31  # Last day of December

    def test_edit_mode_success_message(self, staff_client, active_member, member_type):
        """Test that success message is displayed after update"""
        response = staff_client.post(
            f"/members/edit/{active_member.member_uuid}/",
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": member_type.pk,
                "member_id": "100",
                "milestone_date": "2020-01-01",
                "skip_milestone": "",
                "date_joined": "2020-01-01",
                "override_expiration": "2025-12-31",
            },
        )
        assert response.status_code == 302

        # Follow redirect to member_detail
        detail_response = staff_client.get(response.url)
        assert "updated successfully" in detail_response.content.decode()

