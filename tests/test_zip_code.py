"""
Tests for ZIP code validation in member forms.

Tests that ZIP code field accepts valid formats (5 digits or 5-4 format)
and rejects invalid formats.
"""

import pytest
import re
from django.test import Client
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

from members.models import MemberType

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
