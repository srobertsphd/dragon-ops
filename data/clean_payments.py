#!/usr/bin/env python3
"""
Script to clean the payments CSV file.
Filters out numeric member IDs and splits member names into first and last names.
"""

import pandas as pd
import re
import os


def clean_payments_data(input_file, output_file):
    """
    Clean the payments CSV data according to specifications:
    - Keep only: Payment ID, Member ID (as names), Amount, Date, PaymentMethodID, Receipt No.
    - Filter out rows where Member ID is just a number
    - Split Member ID into first_name and last_name
    - Remove extra whitespace
    """

    # Read the CSV file
    print(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)

    # Select only the columns we need
    columns_to_keep = [
        "Payment ID",
        "Member ID",
        "Amount",
        "Date",
        "PaymentMethodID",
        "Reciept No.",
    ]
    df_cleaned = df[columns_to_keep].copy()

    # Filter out rows where Member ID is just a number (or empty/null)
    def is_valid_name(member_id):
        if pd.isna(member_id) or str(member_id).strip() == "":
            return False
        # Check if it's just a number (with optional decimal points)
        if re.match(r"^\d+\.?\d*$", str(member_id).strip()):
            return False
        return True

    print(f"Original data has {len(df_cleaned)} rows")
    df_cleaned = df_cleaned[df_cleaned["Member ID"].apply(is_valid_name)]
    print(f"After filtering out numeric/empty Member IDs: {len(df_cleaned)} rows")

    # Split Member ID into first_name and last_name
    def split_name(full_name):
        if pd.isna(full_name):
            return "", ""

        # Clean up whitespace and split
        name_parts = str(full_name).strip().split()

        if len(name_parts) == 0:
            return "", ""
        elif len(name_parts) == 1:
            return name_parts[0], ""
        else:
            # First part is first name, everything else is last name
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            return first_name, last_name

    # Apply name splitting
    df_cleaned[["first_name", "last_name"]] = df_cleaned["Member ID"].apply(
        lambda x: pd.Series(split_name(x))
    )

    # Remove the original Member ID column and reorder columns
    df_final = df_cleaned[
        [
            "Payment ID",
            "first_name",
            "last_name",
            "Amount",
            "Date",
            "PaymentMethodID",
            "Reciept No.",
        ]
    ]

    # Clean up any remaining whitespace in all string columns
    string_columns = ["first_name", "last_name", "PaymentMethodID"]
    for col in string_columns:
        df_final[col] = df_final[col].astype(str).str.strip()

    # Replace 'nan' strings with empty strings
    df_final = df_final.replace("nan", "")

    # Save the cleaned data
    print(f"Saving cleaned data to {output_file}...")
    df_final.to_csv(output_file, index=False)

    print(f"Cleaning complete! Final dataset has {len(df_final)} rows")
    print(f"Columns: {list(df_final.columns)}")

    # Show a sample of the cleaned data
    print("\nSample of cleaned data:")
    print(df_final.head(10))

    return df_final


if __name__ == "__main__":
    # Set file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "csv_data", "2025_08_26_Payments.csv")
    output_file = os.path.join(script_dir, "payments_cleaned.csv")

    # Run the cleaning
    clean_payments_data(input_file, output_file)
