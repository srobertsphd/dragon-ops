import pandas as pd

# Configure pandas display options for full width and length
pd.set_option("display.max_columns", None)  # Show all columns
pd.set_option("display.max_rows", None)  # Show all rows
pd.set_option("display.width", None)  # Auto-detect terminal width
pd.set_option("display.max_colwidth", None)  # Show full content of each cell


# Function to standardize dates across files
def standardize_dates(df, date_columns):
    for col in date_columns:
        if col in df.columns:
            # Convert to datetime with coercion for invalid dates
            df[col] = pd.to_datetime(df[col], errors="coerce")

            # Count nulls to report data quality
            null_count = df[col].isna().sum()
            if null_count > 0:
                print(f"Warning: {col} has {null_count} null/invalid dates")

    return df


# # List of date columns to standardize
date_cols = ["Date Joined", "Milestone"]

df = pd.read_csv("csv_data/2025_08_26_Dead.csv")

df = standardize_dates(df, date_cols)

df.info()

# Filter rows where Date Joined is null and display
print("\nDead with null Milestone:")
null_date_joined = df[df["Date Joined"].isna()]
print(null_date_joined)

# Analyze Member ID distribution
print("\nMember ID Analysis:")
print(f"Minimum ID: {df['MemberID'].min()}")
print(f"Maximum ID: {df['MemberID'].max()}")

# Create a set of all possible IDs in the range
all_possible_ids = set(range(int(df["MemberID"].min()), int(df["Member ID"].max()) + 1))

# Get set of actual IDs
actual_ids = set(df["MemberID"])

# Find missing IDs
missing_ids = sorted(all_possible_ids - actual_ids)

if missing_ids:
    print(f"\nMissing MemberIDs ({len(missing_ids)} gaps):")
    print(missing_ids)
else:
    print("\nNo gaps in MemberIDs sequence")

    # Analyze duplicate Member IDs
duplicate_counts = df["MemberID"].value_counts()
duplicates = duplicate_counts[duplicate_counts > 1]

if len(duplicates) > 0:
    print("\nDuplicate Member IDs:")
    print(duplicates)
    print(f"\nTotal number of Member IDs with duplicates: {len(duplicates)}")
    print(f"Total number of duplicate entries: {sum(duplicates) - len(duplicates)}")
else:
    print("\nNo duplicate Member IDs found")

# Analyze duplicate names
print("\nAnalyzing duplicate names:")
name_duplicates = (
    df.groupby(["First Name", "Last Name"]).size().reset_index(name="count")
)
name_duplicates = name_duplicates[name_duplicates["count"] > 1].sort_values(
    "count", ascending=False
)

if len(name_duplicates) > 0:
    print("\nDuplicate names found:")
    print(name_duplicates)
    print(f"\nTotal number of duplicate name combinations: {len(name_duplicates)}")
    print(
        f"Total number of records with duplicate names: {name_duplicates['count'].sum()}"
    )

    # Show full records for duplicates
    print("\nFull records for duplicate names:")
    for _, row in name_duplicates.iterrows():
        print(f"\nRecords for {row['First Name']} {row['Last Name']}:")
        dupe_records = df[
            (df["First Name"] == row["First Name"])
            & (df["Last Name"] == row["Last Name"])
        ]
        print(dupe_records)
else:
    print("\nNo duplicate names found")
