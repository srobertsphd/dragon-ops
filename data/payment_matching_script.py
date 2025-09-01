#!/usr/bin/env python3
"""
Payment Matching Script
Matches payments with members by first name and last name.

This script:
1. Loads cleaned payments and filters to 2025 only
2. Loads cleaned members table
3. Matches payments to members by name
4. Saves matched payments with member information
"""

import pandas as pd
from pathlib import Path


def load_payments():
    """Load payments and filter to 2025 only"""
    payments_file = Path("csv_data/payments_cleaned.csv")
    if not payments_file.exists():
        raise FileNotFoundError(f"Payments file not found: {payments_file}")

    # Load payments
    payments_df = pd.read_csv(payments_file)

    # Convert payment date to datetime and filter to 2025
    payments_df["Date"] = pd.to_datetime(payments_df["Date"], errors="coerce")
    payments_2025 = payments_df[payments_df["Date"].dt.year == 2025].copy()

    return payments_2025


def load_members():
    """Load cleaned members table"""
    members_file = Path("csv_data/2025_08_26_Members_CLEANED.csv")
    if not members_file.exists():
        raise FileNotFoundError(f"Members file not found: {members_file}")

    members = pd.read_csv(members_file)
    return members


def match_payments_to_members(payments_df, members_df):
    """Match payments to members by first name and last name"""
    # Clean member names for matching
    members_df["First_Name_Clean"] = members_df["First Name"].str.strip().str.lower()
    members_df["Last_Name_Clean"] = members_df["Last Name"].str.strip().str.lower()

    # Clean payment names for matching
    payments_df["First_Name_Clean"] = payments_df["first_name"].str.strip().str.lower()
    payments_df["Last_Name_Clean"] = payments_df["last_name"].str.strip().str.lower()

    # Add member info columns to payments
    payments_df["Member_ID"] = None
    payments_df["Member_Type"] = None

    matches_found = 0

    # Match each payment to members
    for idx, payment in payments_df.iterrows():
        payment_first = payment["First_Name_Clean"]
        payment_last = payment["Last_Name_Clean"]

        # Find matching member
        matching_member = members_df[
            (members_df["First_Name_Clean"] == payment_first)
            & (members_df["Last_Name_Clean"] == payment_last)
        ]

        if len(matching_member) > 0:
            # Found match - use first one
            member = matching_member.iloc[0]
            payments_df.at[idx, "Member_ID"] = member["Member ID"]
            payments_df.at[idx, "Member_Type"] = member["Member Type"]
            matches_found += 1

    # Clean up temporary columns
    payments_df = payments_df.drop(["First_Name_Clean", "Last_Name_Clean"], axis=1)

    return payments_df, matches_found


def save_matched_payments(payments_df):
    """Save matched payments to CSV"""
    output_file = Path("csv_data/payments_matched_2025.csv")
    payments_df.to_csv(output_file, index=False)
    return output_file


def main():
    """Main payment matching function"""
    # Load payments (2025 only)
    payments_df = load_payments()

    # Load members
    members_df = load_members()

    # Match payments to members
    matched_payments, match_count = match_payments_to_members(payments_df, members_df)

    # Show info about all processed payments
    print(f"Processed {len(payments_df)} payments from 2025")
    print(f"Found {match_count} matches with members")

    # Filter for rows where Member_ID and Member_Type are not null
    matched_members = matched_payments[
        matched_payments["Member_ID"].notna() & matched_payments["Member_Type"].notna()
    ]

    # Save only the successfully matched payments
    output_file = save_matched_payments(matched_members)

    print(f"Saved {len(matched_members)} matched payments to: {output_file}")
    print(f"Unmatched payments: {len(payments_df) - len(matched_members)}")

    # Display summary of matched payments
    print("\nMatched Payments Summary:")
    print(f"Total matched: {len(matched_members)}")
    if len(matched_members) > 0:
        print("\nMember Type Distribution:")
        print(matched_members["Member_Type"].value_counts())
        print("\nFirst 10 matched payments:")
        print(
            matched_members[
                [
                    "Payment ID",
                    "first_name",
                    "last_name",
                    "Amount",
                    "Date",
                    "Member_ID",
                    "Member_Type",
                ]
            ].head(10)
        )


if __name__ == "__main__":
    main()
