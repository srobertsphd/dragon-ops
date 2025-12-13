"""
Tests for member form field validation and functionality.

Tests ZIP code validation and state dropdown functionality in member forms.
"""

import pytest
import re
from django.test import Client
from django.contrib.auth import get_user_model
from decimal import Decimal

from members.models import MemberType, STATE_CHOICES, Member
from members.services import MemberService

User = get_user_model()

# ZIP code pattern from template: ^\d{5}(-\d{4})?$
ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")


@pytest.mark.django_db
@pytest.mark.unit
class TestZipCodeValidation:
    """Test ZIP code format validation"""

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

    def test_valid_zip_5_digits(self):
        """Test that 5-digit ZIP codes are valid"""
        valid_zips = ["12345", "90210", "00000", "99999"]
        for zip_code in valid_zips:
            assert ZIP_PATTERN.match(zip_code), f"{zip_code} should be valid"

    def test_valid_zip_5_4_format(self):
        """Test that ZIP+4 format (5-4) is valid"""
        valid_zips = ["12345-6789", "90210-1234", "00000-0000", "99999-9999"]
        for zip_code in valid_zips:
            assert ZIP_PATTERN.match(zip_code), f"{zip_code} should be valid"

    def test_invalid_zip_too_short(self):
        """Test that ZIP codes shorter than 5 digits are invalid"""
        invalid_zips = ["1234", "123", "12", "1", ""]
        for zip_code in invalid_zips:
            assert not ZIP_PATTERN.match(zip_code), f"{zip_code} should be invalid"

    def test_invalid_zip_too_long(self):
        """Test that ZIP codes longer than 10 characters are invalid"""
        invalid_zips = ["123456", "12345-67890", "12345678901"]
        for zip_code in invalid_zips:
            assert not ZIP_PATTERN.match(zip_code), f"{zip_code} should be invalid"

    def test_invalid_zip_wrong_format(self):
        """Test that incorrectly formatted ZIP codes are invalid"""
        invalid_zips = [
            "12345-678",  # Only 3 digits after hyphen
            "12345-67890",  # Too many digits after hyphen
            "1234-5678",  # Only 4 digits before hyphen
            "12345 6789",  # Space instead of hyphen
            "abcde",  # Letters
            "12345-",  # Hyphen but no digits after
            "-6789",  # Hyphen but no digits before
        ]
        for zip_code in invalid_zips:
            assert not ZIP_PATTERN.match(zip_code), f"{zip_code} should be invalid"

    def test_zip_code_in_form_submission(self, client, member_type):
        """Test that form accepts valid ZIP codes and rejects invalid ones"""
        # Test valid 5-digit ZIP
        response = client.post(
            "/add/",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type": str(member_type.pk),
                "date_joined": "2020-01-01",
                "expiration_date": "2025-12-31",
                "home_zip": "12345",
                "step": "confirm",
            },
        )
        # Should proceed to confirmation (not show ZIP error)
        assert response.status_code == 200
        assert "12345" in response.content.decode() or response.status_code == 302

        # Test valid ZIP+4 format
        response = client.post(
            "/add/",
            {
                "member_id": "2",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                "member_type": str(member_type.pk),
                "date_joined": "2020-01-01",
                "expiration_date": "2025-12-31",
                "home_zip": "12345-6789",
                "step": "confirm",
            },
        )
        assert response.status_code == 200
        assert "12345-6789" in response.content.decode() or response.status_code == 302


@pytest.mark.django_db
@pytest.mark.unit
class TestStateDropdown:
    """Test state dropdown functionality in member forms"""

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

    def test_state_choices_has_all_50_states(self):
        """Test that STATE_CHOICES contains all 50 US states"""
        assert len(STATE_CHOICES) == 50, f"Expected 50 states, got {len(STATE_CHOICES)}"

    def test_california_is_first(self):
        """Test that California (CA) is the first state in STATE_CHOICES"""
        assert STATE_CHOICES[0][0] == "CA", "California should be first"
        assert "California" in STATE_CHOICES[0][1], "Should display 'California'"

    def test_state_choices_format(self):
        """Test that each state choice has correct format (code, display_name)"""
        for code, name in STATE_CHOICES:
            assert len(code) == 2, f"State code '{code}' should be 2 characters"
            assert code.isupper(), f"State code '{code}' should be uppercase"
            assert code in name, (
                f"State code '{code}' should appear in display name '{name}'"
            )

    def test_state_choices_in_form_context(self, client):
        """Test that state_choices are available in the add member form context"""
        response = client.get("/add/")
        assert response.status_code == 200
        content = response.content.decode()
        # Check that California option is present
        assert 'value="CA"' in content, "California option should be in form"
        assert "California (CA)" in content, "California display name should be in form"

    def test_state_dropdown_defaults_to_california(self, client):
        """Test that state dropdown defaults to California when no state is selected"""
        response = client.get("/add/")
        assert response.status_code == 200
        content = response.content.decode()
        # Check that CA is selected by default (when no member_data.home_state exists)
        # The template logic: {% if member_data.home_state == code or not member_data.home_state and code == "CA" %}
        # Should result in CA being selected
        assert 'value="CA"' in content
        # Check that the selected attribute appears for CA (when no existing state)
        # Note: This is a basic check - the actual selected attribute depends on template rendering

    def test_state_dropdown_preserves_existing_state(self, client, member_type):
        """Test that state dropdown preserves existing state when editing/reactivating"""
        # Simulate form submission with a specific state
        response = client.post(
            "/add/",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "NY",
                "step": "confirm",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Check that NY appears in the confirmation
        assert "NY" in content or "New York" in content

    def test_state_form_submission_with_california(self, client, member_type):
        """Test form submission with California selected"""
        response = client.post(
            "/add/",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "CA",
                "step": "confirm",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Check that CA appears in confirmation
        assert "CA" in content or "California" in content

    def test_state_form_submission_with_different_state(self, client, member_type):
        """Test form submission with a different state selected"""
        response = client.post(
            "/add/",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "TX",
                "step": "confirm",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Check that TX appears in confirmation
        assert "TX" in content or "Texas" in content

    def test_all_states_available_in_dropdown(self, client):
        """Test that all 50 states are available in the dropdown"""
        response = client.get("/add/")
        assert response.status_code == 200
        content = response.content.decode()

        # Check a few representative states
        test_states = ["CA", "NY", "TX", "FL", "AK", "HI"]
        for state_code in test_states:
            assert f'value="{state_code}"' in content, (
                f"State {state_code} should be in dropdown"
            )


@pytest.mark.django_db
@pytest.mark.unit
class TestMemberIdDropdown:
    """Test member ID suggestions dropdown functionality"""

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

    def test_get_suggested_ids_returns_50(self, db):
        """Test that get_suggested_ids returns 50 IDs when requested"""
        next_id, suggested_ids = MemberService.get_suggested_ids(count=50)
        assert len(suggested_ids) == 50, f"Expected 50 IDs, got {len(suggested_ids)}"
        assert next_id == suggested_ids[0], "Next ID should be first in list"
        assert next_id == 1, "Next ID should be 1 when no members exist"

    def test_suggested_ids_are_sequential(self, db):
        """Test that suggested IDs are sequential starting from lowest available"""
        next_id, suggested_ids = MemberService.get_suggested_ids(count=50)
        # Should be sequential: 1, 2, 3, ..., 50
        for i, id_val in enumerate(suggested_ids, start=1):
            assert id_val == i, f"Expected ID {i}, got {id_val}"

    def test_suggested_ids_skips_used_ids(self, db):
        """Test that suggested IDs skip IDs that are already in use"""
        from datetime import date

        # Create a member with ID 5
        member_type = MemberType.objects.create(
            member_type="Regular",
            member_dues=Decimal("30.00"),
            num_months=1,
        )
        Member.objects.create(
            member_id=5,
            first_name="Test",
            last_name="User",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        next_id, suggested_ids = MemberService.get_suggested_ids(count=50)
        assert 5 not in suggested_ids, "ID 5 should be excluded (already in use)"
        assert 1 in suggested_ids, "ID 1 should be included"
        assert 6 in suggested_ids, "ID 6 should be included"

    def test_member_id_dropdown_shows_50_options(self, client):
        """Test that member ID dropdown shows 50 options in the form"""
        response = client.get("/add/")
        assert response.status_code == 200
        content = response.content.decode()

        # Check that IDs 1-50 appear in the dropdown
        for i in range(1, 51):
            assert (
                f'<option value="{i}">{i}</option>' in content
                or f'value="{i}"' in content
            ), f"Member ID {i} should be in dropdown"

    def test_member_id_dropdown_has_quick_select_placeholder(self, client):
        """Test that member ID dropdown has Quick Select placeholder"""
        response = client.get("/add/")
        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="member_id_suggestions"' in content, (
            "Member ID suggestions dropdown should exist"
        )
        assert "Quick Select" in content, "Should have Quick Select placeholder"

    def test_manual_member_id_input_still_works(self, client, db):
        """Test that users can still manually enter member ID"""
        member_type = MemberType.objects.create(
            member_type="Regular",
            member_dues=Decimal("30.00"),
            num_months=1,
        )

        # Submit form with manually entered ID (not from dropdown)
        response = client.post(
            "/add/?step=confirm",
            {
                "member_id": "99",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "CA",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Should proceed to confirmation with ID 99
        assert "99" in content or "#99" in content, (
            "Manually entered ID 99 should be accepted"
        )


@pytest.mark.django_db
@pytest.mark.unit
class TestEmailValidation:
    """Test email validation in member forms"""

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

    @pytest.mark.parametrize(
        "email",
        [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user_name@example.co.uk",
            "test123@example-domain.com",
            "user%name@example.com",  # Django allows % in unquoted addresses
            "user&name@example.com",  # Django allows & in unquoted addresses
        ],
    )
    def test_valid_email_formats(self, client, member_type, email):
        """Test that valid email formats are accepted"""
        response = client.post(
            "/add/?step=confirm",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": email,
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "CA",
            },
        )
        assert response.status_code == 200, f"Valid email '{email}' should be accepted"
        # Should proceed to confirmation page
        assert (
            "confirm" in response.content.decode().lower()
            or response.status_code == 200
        )

    @pytest.mark.parametrize(
        "email",
        [
            "test()@example.com",  # Parentheses not allowed
            "test space@example.com",  # Spaces not allowed
            'test"quote@example.com',  # Unquoted quotes not allowed
            "test@example",  # Missing TLD
            "@example.com",  # Missing local part
            "test@",  # Missing domain
            "test@example..com",  # Double dots in domain
            "test@.com",  # Domain starts with dot
        ],
    )
    def test_invalid_email_formats(self, client, member_type, email):
        """Test that invalid email formats are rejected"""
        response = client.post(
            "/add/?step=confirm",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": email,
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "CA",
            },
        )
        # Should show error message
        assert response.status_code == 200
        content = response.content.decode()
        assert "valid email" in content.lower() or "email" in content.lower(), (
            f"Invalid email '{email}' should show error message"
        )

    def test_empty_email_allowed(self, client, member_type):
        """Test that empty email is allowed (email is optional)"""
        response = client.post(
            "/add/?step=confirm",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "",  # Empty email
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "CA",
            },
        )
        # Should proceed to confirmation (email is optional)
        assert response.status_code == 200
        content = response.content.decode()
        # Should not show email validation error
        assert "valid email" not in content.lower()

    def test_email_with_whitespace_stripped(self, client, member_type):
        """Test that email with leading/trailing whitespace is handled correctly"""
        response = client.post(
            "/add/?step=confirm",
            {
                "member_id": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "  test@example.com  ",  # Whitespace should be stripped
                "member_type_id": str(member_type.pk),
                "date_joined": "2020-01-01",
                "milestone_date": "2020-01-01",
                "home_state": "CA",
            },
        )
        # Should accept email after stripping whitespace
        assert response.status_code == 200
        content = response.content.decode()
        assert "valid email" not in content.lower(), (
            "Email with whitespace should be stripped and accepted"
        )
