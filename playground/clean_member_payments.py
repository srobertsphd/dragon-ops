import pandas as pd

################################################################
# Load the data
################################################################

payments_df = pd.read_excel("../data/new_data/2025_09_02_Member Payments.xlsx")

payments_df.info()

# Define columns to drop
columns_to_drop = [
    "Credit Card #",
    "Cardholder Name",
    "Card Exp. Date",
    "Member ID.1",
    "Selected",
    "Barcode ID",
    "SRVTypID",
    "MailerID",
    "SerialNum",
    "Payment ID",
    "Send to Work?",
    "Company",
    "Title",
    "Work Address",
    "Work City",
    "Work State",
    "Area Code",
    "Zip Code",
    "Work County",
    "Work Phone",
    "Extension",
    "Fax",
    "Due Amount",
    "Payment Method",
    "Home Country",
]

# Drop the columns
payments_df = payments_df.drop(columns=columns_to_drop)

payments_df.info()

################################################################
# clean data
################################################################

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
    "Date": "payment_date",
    "Payments.PaymentMethodID": "payment_method",
    "Reciept No.": "receipt_number",
    "Amount": "payment_amount",
    "Mobile": "mobile_phone",
}

# Apply the column mapping
payments_df = payments_df.rename(columns=column_mapping)


payments_df.info()


################################################################
# Convert date columns to datetime
################################################################

payments_df[["date_joined", "milestone_date", "expiration_date", "payment_date"]] = (
    payments_df[
        ["date_joined", "milestone_date", "expiration_date", "payment_date"]
    ].apply(pd.to_datetime, errors="coerce")
)

payments_df.info()


################################################################
# compare to make certain the payment member info matches the member info
################################################################

members_df = pd.read_csv("data/current_members.csv")

members_df.info()


def compare_members(payments_df, members_df):
    """
    Compare if all members in payments_df exist in members_df
    based on member_id, first_name, and last_name
    """
    # Create sets of member tuples for comparison
    payments_members = set(
        payments_df[["member_id", "first_name", "last_name"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )

    members_list = set(
        members_df[["member_id", "first_name", "last_name"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )

    # Find matches and mismatches
    matches = payments_members.intersection(members_list)
    payments_not_in_members = payments_members - members_list

    # Return simple comparison results
    return {
        "total_unique_payment_members": len(payments_members),
        "total_members_in_list": len(members_list),
        "matches_found": len(matches),
        "payments_members_not_found": len(payments_not_in_members),
        "all_payments_members_exist": len(payments_not_in_members) == 0,
    }


# Use the function
result = compare_members(payments_df, members_df)
print(result)

################################################################
# check the payment types
################################################################

payments_df["payment_method"].value_counts(dropna=False)

payments_df[payments_df["payment_method"] == "Partial Payment"]

payments_df[payments_df["payment_method"].isna()]

################################################################
# drop the one line with no payment method
################################################################

# Drop rows where payment_method is NA
payments_df = payments_df.dropna(subset=["payment_method"])

payments_df.info()

################################################################
# drop null payment amounts
################################################################

payments_df[payments_df["payment_amount"].isna()]


payments_df = payments_df.dropna(subset=["payment_amount"])


################################################################
# save the cleaned data
################################################################

payments_df.to_csv("data/current_payments.csv", index=False)
