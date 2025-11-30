"""
Tests for Member Service (Step 4: Extract Member Service)

Tests the MemberService class methods:
- get_suggested_ids()
- create_member()
- check_duplicate_members()
"""

import pytest
from datetime import date

from members.services import MemberService
from members.models import Member, MemberType


@pytest.mark.django_db
@pytest.mark.unit
class TestMemberServiceGetSuggestedIds:
    """Test MemberService.get_suggested_ids() method"""

    @pytest.fixture
    def member_type(self, db):
        """Create a test member type"""
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=30.00,
            num_months=1,
        )

    def test_get_suggested_ids_default_count(self, db):
        """Test that get_suggested_ids returns 5 IDs by default"""
        next_id, suggested_ids = MemberService.get_suggested_ids()

        assert isinstance(next_id, int)
        assert isinstance(suggested_ids, list)
        assert len(suggested_ids) == 5
        assert next_id == suggested_ids[0]

    def test_get_suggested_ids_custom_count(self, db):
        """Test that get_suggested_ids returns requested number of IDs"""
        next_id, suggested_ids = MemberService.get_suggested_ids(count=3)

        assert len(suggested_ids) == 3
        assert next_id == suggested_ids[0]

    def test_get_suggested_ids_returns_available_ids(self, db, member_type):
        """Test that suggested IDs are actually available (not in use)"""
        # Create a member with ID 1
        Member.objects.create(
            first_name="Test",
            last_name="Member",
            email="test@example.com",
            member_type=member_type,
            status="active",
            member_id=1,
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        next_id, suggested_ids = MemberService.get_suggested_ids(count=5)

        # ID 1 should not be in suggested_ids
        assert 1 not in suggested_ids
        # Next ID should be 2 (first available)
        assert next_id == 2
        assert 2 in suggested_ids

    def test_get_suggested_ids_skips_inactive_members(self, db, member_type):
        """Test that inactive members don't block ID suggestions"""
        # Create an inactive member with ID 1
        Member.objects.create(
            first_name="Inactive",
            last_name="Member",
            email="inactive@example.com",
            member_type=member_type,
            status="inactive",
            member_id=1,
            expiration_date=date(2024, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        next_id, suggested_ids = MemberService.get_suggested_ids(count=5)

        # ID 1 should be available (inactive members don't block)
        assert 1 in suggested_ids
        assert next_id == 1

    def test_get_suggested_ids_handles_no_available_ids(self, db, member_type):
        """Test behavior when many IDs are used"""
        # Create members with IDs 1-10
        for i in range(1, 11):
            Member.objects.create(
                first_name=f"Test{i}",
                last_name="Member",
                email=f"test{i}@example.com",
                member_type=member_type,
                status="active",
                member_id=i,
                expiration_date=date(2025, 12, 31),
                date_joined=date(2020, 1, 1),
            )

        next_id, suggested_ids = MemberService.get_suggested_ids(count=5)

        # Should return IDs starting from 11
        assert next_id == 11
        assert 11 in suggested_ids
        assert len(suggested_ids) == 5

    def test_get_suggested_ids_returns_correct_format(self, db):
        """Test that return value is correct tuple format"""
        result = MemberService.get_suggested_ids(count=3)

        assert isinstance(result, tuple)
        assert len(result) == 2
        next_id, suggested_ids = result
        assert isinstance(next_id, int)
        assert isinstance(suggested_ids, list)
        assert all(isinstance(id_num, int) for id_num in suggested_ids)


@pytest.mark.django_db
@pytest.mark.integration
class TestMemberServiceCreateMember:
    """Test MemberService.create_member() method"""

    @pytest.fixture
    def member_type(self, db):
        """Create a test member type"""
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=30.00,
            num_months=1,
        )

    @pytest.fixture
    def member_data(self, member_type):
        """Create sample member data"""
        return {
            "member_type_id": str(member_type.pk),
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "member_id": 100,
            "milestone_date": "2020-01-15",
            "date_joined": "2025-01-01",
            "home_address": "123 Main St",
            "home_city": "Anytown",
            "home_state": "CA",
            "home_zip": "12345",
            "home_phone": "555-1234",
            "initial_expiration": "2025-12-31",
        }

    def test_create_member_creates_member(self, db, member_data):
        """Test that create_member creates a Member record"""
        initial_count = Member.objects.count()

        member = MemberService.create_member(member_data)

        assert Member.objects.count() == initial_count + 1
        assert isinstance(member, Member)
        assert member.first_name == "John"
        assert member.last_name == "Doe"

    def test_create_member_sets_correct_member_id(self, db, member_data):
        """Test that member_id is set correctly"""
        member = MemberService.create_member(member_data)

        assert member.member_id == 100

    def test_create_member_sets_all_fields(self, db, member_data):
        """Test that all member fields are set correctly"""
        member = MemberService.create_member(member_data)

        assert member.first_name == "John"
        assert member.last_name == "Doe"
        assert member.email == "john.doe@example.com"
        assert member.member_id == 100
        assert member.milestone_date == date(2020, 1, 15)
        assert member.date_joined == date(2025, 1, 1)
        assert member.home_address == "123 Main St"
        assert member.home_city == "Anytown"
        assert member.home_state == "CA"
        assert member.home_zip == "12345"
        assert member.home_phone == "555-1234"
        assert member.expiration_date == date(2025, 12, 31)

    def test_create_member_sets_member_type(self, db, member_type, member_data):
        """Test that member_type is set correctly"""
        member = MemberService.create_member(member_data)

        assert member.member_type == member_type

    def test_create_member_handles_empty_optional_fields(self, db, member_type):
        """Test that optional fields can be empty"""
        member_data = {
            "member_type_id": str(member_type.pk),
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "",
            "member_id": 200,
            "milestone_date": "2020-06-01",
            "date_joined": "2025-01-01",
            "home_address": "",
            "home_city": "",
            "home_state": "",
            "home_zip": "",
            "home_phone": "",
            "initial_expiration": "2025-12-31",
        }

        member = MemberService.create_member(member_data)

        assert member.email == ""
        assert member.home_address == ""
        assert member.home_city == ""

    def test_create_member_returns_member_instance(self, db, member_data):
        """Test that create_member returns a Member instance"""
        member = MemberService.create_member(member_data)

        assert isinstance(member, Member)
        assert hasattr(member, "member_uuid")
        assert hasattr(member, "full_name")


@pytest.mark.django_db
@pytest.mark.unit
class TestMemberServiceCheckDuplicateMembers:
    """Test MemberService.check_duplicate_members() method"""

    @pytest.fixture
    def member_type(self, db):
        """Create a test member type"""
        return MemberType.objects.create(
            member_type="Regular",
            member_dues=30.00,
            num_months=1,
        )

    def test_check_duplicate_members_name_match(self, db, member_type):
        """Test that name matching works (case-insensitive)"""
        # Create an existing member
        existing_member = Member.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        # Check for duplicate with exact match
        matches = MemberService.check_duplicate_members("John", "Doe", "", "")

        assert len(matches) == 1
        assert matches[0]["member"] == existing_member
        assert matches[0]["match_reason"] == "name"
        assert matches[0]["match_text"] == "John Doe"

        # Check for duplicate with different case (case-insensitive)
        matches_case = MemberService.check_duplicate_members("JOHN", "DOE", "", "")

        assert len(matches_case) == 1
        assert matches_case[0]["member"] == existing_member

    def test_check_duplicate_members_phone_match(self, db, member_type):
        """Test that phone matching works (if phone provided)"""
        # Create an existing member with phone
        existing_member = Member.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            home_phone="555-1234",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        # Check for duplicate by phone
        matches = MemberService.check_duplicate_members(
            "Different", "Name", "", "555-1234"
        )

        assert len(matches) == 1
        assert matches[0]["member"] == existing_member
        assert matches[0]["match_reason"] == "phone"
        assert matches[0]["match_text"] == "555-1234"

    def test_check_duplicate_members_email_match(self, db, member_type):
        """Test that email matching works (case-insensitive, if email provided)"""
        # Create an existing member with email
        existing_member = Member.objects.create(
            first_name="Bob",
            last_name="Johnson",
            email="bob.johnson@example.com",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        # Check for duplicate by email (exact match)
        matches = MemberService.check_duplicate_members(
            "Different", "Name", "bob.johnson@example.com", ""
        )

        assert len(matches) == 1
        assert matches[0]["member"] == existing_member
        assert matches[0]["match_reason"] == "email"
        assert matches[0]["match_text"] == "bob.johnson@example.com"

        # Check for duplicate by email (different case - case-insensitive)
        matches_case = MemberService.check_duplicate_members(
            "Different", "Name", "BOB.JOHNSON@EXAMPLE.COM", ""
        )

        assert len(matches_case) == 1
        assert matches_case[0]["member"] == existing_member

    def test_check_duplicate_members_multiple_matches_same_member(
        self, db, member_type
    ):
        """Test that same member matched by multiple criteria appears only once"""
        # Create an existing member matching name, phone, and email
        existing_member = Member.objects.create(
            first_name="Alice",
            last_name="Williams",
            email="alice.williams@example.com",
            home_phone="555-9999",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        # Check for duplicate - should match by name, phone, and email
        matches = MemberService.check_duplicate_members(
            "Alice", "Williams", "alice.williams@example.com", "555-9999"
        )

        # Should only appear once (matched by name first)
        assert len(matches) == 1
        assert matches[0]["member"] == existing_member
        assert matches[0]["match_reason"] == "name"

    def test_check_duplicate_members_empty_phone_email(self, db, member_type):
        """Test that empty phone/email fields don't cause errors"""
        # Create an existing member
        Member.objects.create(
            first_name="Test",
            last_name="Member",
            email="test@example.com",
            home_phone="555-0000",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        # Check with empty phone and email - should not match
        matches = MemberService.check_duplicate_members("Different", "Name", "", "")

        assert len(matches) == 0

        # Check with empty phone but matching email
        matches_email = MemberService.check_duplicate_members(
            "Different", "Name", "test@example.com", ""
        )

        assert len(matches_email) == 1

    def test_check_duplicate_members_no_matches(self, db, member_type):
        """Test that no matches returns empty list"""
        # Create an existing member
        Member.objects.create(
            first_name="Existing",
            last_name="Member",
            email="existing@example.com",
            home_phone="555-1111",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        # Check for completely different member
        matches = MemberService.check_duplicate_members(
            "New", "Member", "new@example.com", "555-2222"
        )

        assert isinstance(matches, list)
        assert len(matches) == 0

    def test_check_duplicate_members_multiple_different_members(self, db, member_type):
        """Test that multiple different members matching are all returned"""
        # Create multiple existing members with same name
        member1 = Member.objects.create(
            first_name="John",
            last_name="Doe",
            email="john1@example.com",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        member2 = Member.objects.create(
            first_name="John",
            last_name="Doe",
            email="john2@example.com",
            member_type=member_type,
            status="inactive",
            expiration_date=date(2024, 12, 31),
            date_joined=date(2019, 1, 1),
        )

        # Check for duplicate by name - should find both
        matches = MemberService.check_duplicate_members("John", "Doe", "", "")

        assert len(matches) == 2
        member_pks = [m["member"].pk for m in matches]
        assert member1.pk in member_pks
        assert member2.pk in member_pks
        # Both should be matched by name
        assert all(m["match_reason"] == "name" for m in matches)

    def test_check_duplicate_members_all_statuses(self, db, member_type):
        """Test that duplicate check works for all member statuses"""
        # Create members with different statuses
        active_member = Member.objects.create(
            first_name="Status",
            last_name="Test",
            email="active@example.com",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        inactive_member = Member.objects.create(
            first_name="Status",
            last_name="Test",
            email="inactive@example.com",
            member_type=member_type,
            status="inactive",
            expiration_date=date(2024, 12, 31),
            date_joined=date(2019, 1, 1),
        )

        deceased_member = Member.objects.create(
            first_name="Status",
            last_name="Test",
            email="deceased@example.com",
            member_type=member_type,
            status="deceased",
            expiration_date=date(2023, 12, 31),
            date_joined=date(2018, 1, 1),
        )

        # Check for duplicates - should find all three
        matches = MemberService.check_duplicate_members("Status", "Test", "", "")

        assert len(matches) == 3
        member_pks = [m["member"].pk for m in matches]
        assert active_member.pk in member_pks
        assert inactive_member.pk in member_pks
        assert deceased_member.pk in member_pks

    def test_check_duplicate_members_return_format(self, db, member_type):
        """Test that return value has correct format"""
        # Create an existing member
        existing_member = Member.objects.create(
            first_name="Format",
            last_name="Test",
            email="format@example.com",
            home_phone="555-8888",
            member_type=member_type,
            status="active",
            expiration_date=date(2025, 12, 31),
            date_joined=date(2020, 1, 1),
        )

        matches = MemberService.check_duplicate_members(
            "Format", "Test", "format@example.com", "555-8888"
        )

        assert isinstance(matches, list)
        assert len(matches) == 1

        match = matches[0]
        assert isinstance(match, dict)
        assert "member" in match
        assert "match_reason" in match
        assert "match_text" in match
        assert isinstance(match["member"], Member)
        assert isinstance(match["match_reason"], str)
        assert isinstance(match["match_text"], str)
        assert match["member"] == existing_member
