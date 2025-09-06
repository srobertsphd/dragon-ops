import pandas as pd

################################################################
# Member Data Cleanup
################################################################


members_df = pd.read_excel(
    "../data/2025_09_02/excel_files/2025_09_02_Members-Data.xlsx"
)

members_df.info()

# Define the column mapping
column_mapping = {
    "Member ID": "member_id",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Member Type": "member_type",
    "Home Address": "home_address",
    "Home City": "home_city",
    "Home State": "home_state",
    "Home Zip": "home_zip",
    "Home Phone": "home_phone",
    "E Mail Name": "email",
    "Date Joined": "date_joined",
    "Milestone": "milestone_date",
    "Expires": "expiration_date",
}

# Apply the column mapping
members_df = members_df.rename(columns=column_mapping)

members_df.info()

################################################################
# Convert date columns to datetime, handling out-of-bounds dates
################################################################

members_df[["date_joined", "milestone_date", "expiration_date"]] = members_df[
    ["date_joined", "milestone_date", "expiration_date"]
].apply(pd.to_datetime, errors="coerce")

members_df.info()

################################################################
# Set lifetime members' expiration for PostgreSQL (non-nullable date field)
###############################################################

lifetime_mask = members_df["member_type"].str.lower() == "life"

# Use a far future date for lifetime members (PostgreSQL compatible)
LIFETIME_EXPIRY_DATE = pd.Timestamp("2099-12-31")
members_df.loc[lifetime_mask, "expiration_date"] = LIFETIME_EXPIRY_DATE

print(
    f"Setting {lifetime_mask.sum()} lifetime members to expire on {LIFETIME_EXPIRY_DATE.date()}"
)

################################################################
# Check for problems with member types (reinstate or NaN)
################################################################

members_df["member_type"].value_counts(dropna=False)

# print out the promble member names
problem_members = members_df[
    (members_df["member_type"].isna()) | (members_df["member_type"] == "Reinstate")
][["first_name", "last_name"]].values.tolist()

print(f"Problem members: {problem_members}")

# replace the problem member types with Regular
members_df.loc[
    (members_df["member_type"].isna()) | (members_df["member_type"] == "Reinstate"),
    "member_type",
] = "Regular"

members_df.info()

################################################################
# clean home_zip field
################################################################
# Clean home_zip: keep only 5-digit zip code, remove hyphen and everything after
members_df["home_zip"] = members_df["home_zip"].str.split("-").str[0].str.strip()

members_df.home_zip.value_counts(dropna=False)

################################################################
# clean home_state field
################################################################
home_state_counts = members_df["home_state"].value_counts(dropna=False)
print(home_state_counts)

# Complete state mapping to proper 2-letter uppercase abbreviations
state_mapping = {
    "Ca": "CA",  # California
    "CA.": "CA",  # California with period
    "ca": "CA",  # California lowercase
    "Il": "IL",  # Illinois
    "Tn": "TN",  # Tennessee
    "Id": "ID",  # Idaho
    "Mn": "MN",  # Minnesota
    "HW": "HI",  # Hawaii (assuming HW is a typo)
}

members_df["home_state"] = members_df["home_state"].replace(state_mapping)

members_df.home_state.value_counts(dropna=False)

################################################################
# clean home_phone field
################################################################

members_df.home_phone.value_counts(dropna=False)


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
check_phone_format(members_df["home_phone"])

################################################################
# Save the cleaned data
################################################################

members_df.to_csv("../data/2025_09_02/csv_data/current_members.csv", index=False)

################################################################
# Show some useful info about the data
################################################################

lifetime_count = (members_df["expiration_date"] == LIFETIME_EXPIRY_DATE).sum()
print(f"\nLifetime members (expire {LIFETIME_EXPIRY_DATE.date()}): {lifetime_count}")
print(f"Regular members with normal expiration: {len(members_df) - lifetime_count}")

# Example: Find expired members (excluding lifetime members)
today = pd.Timestamp.now()
expired_members = members_df[
    (members_df["expiration_date"] < today)
    & (members_df["expiration_date"] != LIFETIME_EXPIRY_DATE)
]
print(f"Expired members (excluding lifetime): {len(expired_members)}")
