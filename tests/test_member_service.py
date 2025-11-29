"""
Tests for Member Service (Step 4: Extract Member Service)

Tests the MemberService class methods:
- get_suggested_ids()
- create_member()

Note: These tests will skip until MemberService is created.
"""

import pytest


@pytest.mark.unit
class TestMemberServiceGetSuggestedIds:
    """Test MemberService.get_suggested_ids() method"""

    def test_service_not_yet_created(self):
        """Test that MemberService doesn't exist yet (expected before Step 4)"""
        try:
            from members.services import MemberService  # noqa: F401

            pytest.fail("MemberService should not exist yet")
        except ImportError:
            # Expected - service not created yet
            pass


@pytest.mark.integration
class TestMemberServiceCreateMember:
    """Test MemberService.create_member() method"""

    def test_service_not_yet_created(self):
        """Test that MemberService doesn't exist yet (expected before Step 4)"""
        try:
            from members.services import MemberService  # noqa: F401

            pytest.fail("MemberService should not exist yet")
        except ImportError:
            # Expected - service not created yet
            pass
