#!/usr/bin/env python3
"""
Data Script Data Cleaning
Functional script to clean and match member data between CSV files.

This script:
1. Reads the current members CSV and drops SerialNum field
2. Matches with old members data to add member_type
3. Saves only members with member types
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_and_clean_current_members():
    """Load current members CSV and drop SerialNum field"""
    current_file = Path("csv_data/2025_08_26_Members.csv")
    if not current_file.exists():
        raise FileNotFoundError(f"File not found: {current_file}")

    current_df = pd.read_csv(current_file)

    # Drop SerialNum field if it exists
    if "SerialNum" in current_df.columns:
        current_df = current_df.drop("SerialNum", axis=1)

    return current_df


def load_old_members():
    """Load old members data for matching"""
    old_file = Path("csv_data/OLD_Members-Data.csv")
    if not old_file.exists():
        raise FileNotFoundError(f"File not found: {old_file}")

    return pd.read_csv(old_file)


def match_member_types(current_df, old_df):
    """Match members and add member_type from old data"""
    # Add member_type column to current_df (initially empty)
    current_df["Member Type"] = np.nan

    # Iterate through current members
    for idx, current_member in current_df.iterrows():
        current_id = current_member["Member ID"]
        current_first = str(current_member["First Name"]).strip().lower()
        current_last = str(current_member["Last Name"]).strip().lower()

        # Skip if any field is missing
        if pd.isna(current_id) or current_first == "nan" or current_last == "nan":
            continue

        # Look for match in old data
        matching_old = old_df[
            (old_df["Member ID"] == current_id)
            & (old_df["First Name"].str.strip().str.lower() == current_first)
            & (old_df["Last Name"].str.strip().str.lower() == current_last)
        ]

        if len(matching_old) > 0:
            # Found match - get member type from first matching record
            member_type = matching_old.iloc[0]["Member Type"]
            current_df.at[idx, "Member Type"] = member_type

    return current_df


def save_members_with_types(df):
    """Save only members that have member types to a new file"""
    # Filter to only members with member types
    members_with_types = df[df["Member Type"].notna()]

    output_file = Path("csv_data/2025_08_26_Members_CLEANED.csv")
    members_with_types.to_csv(output_file, index=False)

    return len(members_with_types)


def main():
    """Main data cleaning function"""
    # Load current members data
    current_df = load_and_clean_current_members()

    # Load old members data
    old_df = load_old_members()

    # Match member types
    cleaned_df = match_member_types(current_df, old_df)

    # Save only members with types
    save_members_with_types(cleaned_df)


if __name__ == "__main__":
    main()
