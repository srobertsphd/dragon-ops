"""
Utility functions for date calculations.

These functions handle date manipulation for membership expiration dates.
"""

import calendar


def ensure_end_of_month(date_obj):
    """Force date to be the last day of its month"""
    last_day = calendar.monthrange(date_obj.year, date_obj.month)[1]
    return date_obj.replace(day=last_day)


def add_months_to_date(date_obj, months):
    """Add months to a date and return the last day of the resulting month

    Examples:
    - Current expiration: Mar 15, 2025 + 1 month = Mar 31, 2025
    - Current expiration: Jan 31, 2025 + 1 month = Feb 28, 2025 (or Feb 29 in leap year)
    - Current expiration: Dec 15, 2024 + 2 months = Feb 29, 2025

    This ensures all memberships expire at the end of the month regardless of payment date.
    """
    # Calculate the target year and month
    month = date_obj.month - 1 + months
    year = date_obj.year + month // 12
    month = month % 12 + 1

    # Get the last day of the target month
    last_day = calendar.monthrange(year, month)[1]

    return date_obj.replace(year=year, month=month, day=last_day)
