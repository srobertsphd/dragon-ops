"""
Tests for utility functions (Step 1: Extract Utility Functions)

Tests the date utility functions:
- ensure_end_of_month()
- add_months_to_date()

These tests validate the current implementation and will ensure
the refactored version works identically.
"""

import pytest
from datetime import date
from members.views import ensure_end_of_month, add_months_to_date


@pytest.mark.unit
class TestEnsureEndOfMonth:
    """Test ensure_end_of_month utility function"""

    def test_mid_month_date(self):
        """Test that mid-month date becomes last day of month"""
        test_date = date(2025, 3, 15)
        result = ensure_end_of_month(test_date)
        assert result == date(2025, 3, 31)

    def test_already_last_day(self):
        """Test that last day of month stays the same"""
        test_date = date(2025, 3, 31)
        result = ensure_end_of_month(test_date)
        assert result == date(2025, 3, 31)

    def test_february_non_leap_year(self):
        """Test February in non-leap year"""
        test_date = date(2025, 2, 15)
        result = ensure_end_of_month(test_date)
        assert result == date(2025, 2, 28)

    def test_february_leap_year(self):
        """Test February in leap year"""
        test_date = date(2024, 2, 15)
        result = ensure_end_of_month(test_date)
        assert result == date(2024, 2, 29)


@pytest.mark.unit
class TestAddMonthsToDate:
    """Test add_months_to_date utility function"""

    def test_add_one_month_mid_month(self):
        """Test adding 1 month to mid-month date"""
        test_date = date(2025, 3, 15)
        result = add_months_to_date(test_date, 1)
        # Mar 15 + 1 month = April 30 (last day of April)
        assert result == date(2025, 4, 30)

    def test_add_one_month_end_of_month(self):
        """Test adding 1 month when current date is end of month"""
        test_date = date(2025, 1, 31)
        result = add_months_to_date(test_date, 1)
        # January 31 + 1 month = February 28 (or 29 in leap year)
        assert result == date(2025, 2, 28)

    def test_add_two_months(self):
        """Test adding 2 months"""
        test_date = date(2025, 3, 15)
        result = add_months_to_date(test_date, 2)
        # Mar 15 + 2 months = May 31 (last day of May)
        assert result == date(2025, 5, 31)

    def test_add_months_cross_year_boundary(self):
        """Test adding months that cross year boundary"""
        test_date = date(2025, 11, 15)
        result = add_months_to_date(test_date, 2)
        assert result == date(2026, 1, 31)
