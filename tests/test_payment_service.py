"""
Tests for Payment Service (Step 3: Extract Payment Service)

Tests the PaymentService class methods:
- calculate_expiration()
- process_payment()

Note: These tests will skip until PaymentService is created.
"""

import pytest


@pytest.mark.unit
class TestPaymentServiceCalculateExpiration:
    """Test PaymentService.calculate_expiration() method"""

    def test_service_not_yet_created(self):
        """Test that PaymentService doesn't exist yet (expected before Step 3)"""
        try:
            from members.services import PaymentService  # noqa: F401

            pytest.fail("PaymentService should not exist yet")
        except ImportError:
            # Expected - service not created yet
            pass


@pytest.mark.integration
class TestPaymentServiceProcessPayment:
    """Test PaymentService.process_payment() method"""

    def test_service_not_yet_created(self):
        """Test that PaymentService doesn't exist yet (expected before Step 3)"""
        try:
            from members.services import PaymentService  # noqa: F401

            pytest.fail("PaymentService should not exist yet")
        except ImportError:
            # Expected - service not created yet
            pass
