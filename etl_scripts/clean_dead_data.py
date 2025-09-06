import pandas as pd


dead_df = pd.read_excel("../data/2025_09_02/excel_files/2025_09_02_Dead.xlsx")

dead_df.info()

# Define the column mapping to match established naming conventions
dead_column_mapping = {
    "DeadID": "dead_id",
    "MemberID": "member_id",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Member Type": "member_type",
    "Home Address": "home_address",
    "Home City": "home_city",
    "Home State": "home_state",
    "Home Zip": "home_zip",
    "Home Phone": "home_phone",
    "E Mail Name": "email",
    "Milestone": "milestone_date",
    "Date Joined": "date_joined",
    "Expires": "expiration_date",
    "Payment Method": "payment_method",
}

# Apply the column mapping
dead_df = dead_df.rename(columns=dead_column_mapping)

# drop the one line with no member id
dead_df.head(20)

dead_df.info()

################################################################
# drop unused columns
################################################################
# Drop dead_id and payment_method columns
dead_df = dead_df.drop(columns=["dead_id", "payment_method"])

dead_df.info()

dead_df.describe()

################################################################

# Find duplicate first_name, last_name combinations
duplicates = dead_df[dead_df.duplicated(subset=["first_name", "last_name"], keep=False)]

# Count unique duplicate combinations
duplicate_combinations = dead_df[["first_name", "last_name"]].value_counts()
duplicate_combinations = duplicate_combinations[duplicate_combinations > 1]

print(f"Total records with duplicate name combinations: {len(duplicates)}")
print(
    f"Number of unique name combinations that have duplicates: {len(duplicate_combinations)}"
)
print("\nDuplicate name combinations:")
print(duplicate_combinations)

# Optionally show the actual duplicate records
print("\nDetailed view of duplicate records:")
print(
    duplicates[["first_name", "last_name", "member_id"]].sort_values(
        ["first_name", "last_name"]
    )
)

################################################################


def deduplicate_by_latest_expiration(df):
    """
    Remove duplicates by keeping the record with the most recent expiration_date
    for each first_name, last_name combination
    """
    # Group by first_name and last_name, then find the index of the row
    # with the maximum expiration_date for each group
    latest_indices = df.groupby(["first_name", "last_name"])["expiration_date"].idxmax()

    # Select only those rows
    deduplicated_df = df.loc[latest_indices].copy()

    # Sort by last_name, first_name for easier review
    deduplicated_df = deduplicated_df.sort_values(["last_name", "first_name"])

    # Reset index
    deduplicated_df = deduplicated_df.reset_index(drop=True)

    print(f"Original records: {len(df)}")
    print(f"After deduplication: {len(deduplicated_df)}")
    print(f"Records removed: {len(df) - len(deduplicated_df)}")

    return deduplicated_df


# Apply deduplication
dead_df = deduplicate_by_latest_expiration(dead_df)

# Verify no duplicates remain
remaining_duplicates = dead_df[["first_name", "last_name"]].value_counts()
remaining_duplicates = remaining_duplicates[remaining_duplicates > 1]
print(f"\nRemaining duplicate combinations: {len(remaining_duplicates)}")

################################################################
# save the cleaned data
################################################################
dead_df.info()

dead_df.home_state.value_counts(dropna=False)

# State mapping to proper 2-letter uppercase abbreviations
state_mapping = {
    "Ca": "CA",  # California
    "Az": "AZ",  # Arizona
    "Or": "OR",  # Oregon
    "Wy": "WY",  # Wyoming
    "nebr": "NE",  # Nebraska
    "Utah": "UT",  # Utah
}

# Apply the state mapping
dead_df["home_state"] = dead_df["home_state"].replace(state_mapping)

dead_df.info()

################################################################

# Convert member_id to integer (handles NaN values)
dead_df["member_id"] = dead_df["member_id"].astype("Int64")

dead_df.info()

dead_df.home_phone.value_counts(dropna=False).tolist()


################################################################
def check_phone_format(phone_series):
    """
    Check that all non-null phone numbers follow format: (XXX) XXX-XXXX
    Returns True if all are properly formatted, False otherwise
    """
    # Pattern: (XXX) XXX-XXXX - exactly this format
    pattern = r"^\(\d{3}\) \d{3}-\d{4}$"

    # Filter out NaN values and check non-null phones
    non_null_phones = phone_series.dropna()

    # Check each phone number against the pattern
    properly_formatted = non_null_phones.str.match(pattern)

    # Report results
    total_phones = len(non_null_phones)
    correct_format = properly_formatted.sum()

    print(f"Phone numbers checked: {total_phones}")
    print(f"Properly formatted: {correct_format}")
    print(f"Incorrectly formatted: {total_phones - correct_format}")

    if correct_format == total_phones:
        print("✅ All phone numbers are properly formatted!")
        return True
    else:
        print("❌ Some phone numbers need formatting fixes")
        # Show examples of incorrectly formatted ones
        bad_phones = non_null_phones[~properly_formatted].head(5)
        print("Examples of incorrect formatting:")
        print(bad_phones.tolist())
        return False


# Use it:
check_phone_format(dead_df["home_phone"])


def fix_phone_formatting(df, phone_col="home_phone"):
    """
    Fix phone number formatting and return DataFrame of corrected rows
    """
    import re

    pattern = r"^\(\d{3}\) \d{3}-\d{4}$"
    non_null_phones = df[phone_col].dropna()
    incorrect_mask = ~non_null_phones.str.match(pattern)
    incorrect_rows = df[df[phone_col].isin(non_null_phones[incorrect_mask])]

    if len(incorrect_rows) == 0:
        print("✅ All phone numbers already properly formatted!")
        return pd.DataFrame()

    print(f"Fixing {len(incorrect_rows)} phone numbers:")

    for idx, row in incorrect_rows.iterrows():
        old_phone = row[phone_col]
        # Extract digits and reformat
        digits = re.sub(r"\D", "", str(old_phone))
        if len(digits) == 10:
            new_phone = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            df.at[idx, phone_col] = new_phone
            print(f"  {old_phone} → {new_phone}")

    return incorrect_rows


# Use the function
fixed_rows = fix_phone_formatting(dead_df)

################################################################
# fix malformed phone numbers
################################################################


def fix_malformed_phone_numbers(df, phone_col="home_phone"):
    """
    Fix phone numbers with incomplete area codes by setting them to 408
    """
    import re

    # Pattern to find malformed numbers like (6) or (40)
    malformed_pattern = r"^\(\d{1,2}\) \d{3}-\d{4}$"

    malformed_mask = df[phone_col].str.match(malformed_pattern, na=False)
    malformed_rows = df[malformed_mask]

    if len(malformed_rows) == 0:
        print("No malformed phone numbers found")
        return pd.DataFrame()

    print(f"Fixing {len(malformed_rows)} malformed phone numbers:")

    for idx, row in malformed_rows.iterrows():
        old_phone = row[phone_col]
        # Extract the last 7 digits and add 408 area code
        digits = re.sub(r"\D", "", old_phone)[-7:]  # Get last 7 digits
        new_phone = f"(408) {digits[:3]}-{digits[3:]}"
        df.at[idx, phone_col] = new_phone
        print(f"  {old_phone} → {new_phone}")

    return malformed_rows


# Use the function
fixed_malformed_rows = fix_malformed_phone_numbers(dead_df)


################################################################
# fix zip codes
################################################################

dead_df.home_zip.value_counts(dropna=False)

# Clean home_zip: keep only 5-digit zip code, remove hyphen and everything after
dead_df["home_zip"] = dead_df["home_zip"].str.split("-").str[0].str.strip()

dead_df.home_zip.value_counts(dropna=False)

# save the cleaned data
################################################################
dead_df.to_csv("../data/2025_09_02/csv_data/current_dead.csv", index=False)
