#!/usr/bin/env python3
"""
Alano Club CSV Data Explorer
Analyzes all CSV files and provides comprehensive data insights.
"""

import pandas as pd
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")


def analyze_dates(df, date_columns):
    """Analyze date columns and convert them to proper datetime format"""
    date_info = {}

    for col in date_columns:
        if col in df.columns:
            print(f"\n📅 Date Analysis for '{col}':")

            # Show original data types and sample values
            print(f"   Original dtype: {df[col].dtype}")
            print(f"   Non-null values: {df[col].notna().sum()}/{len(df)}")

            # Show sample values before conversion
            sample_values = df[col].dropna().head(3).tolist()
            print(f"   Sample original values: {sample_values}")

            # Try to convert to datetime
            try:
                df[col + "_converted"] = pd.to_datetime(df[col], errors="coerce")
                converted_count = df[col + "_converted"].notna().sum()
                print(
                    f"   ✅ Successfully converted: {converted_count}/{df[col].notna().sum()} values"
                )

                if converted_count > 0:
                    date_range = f"{df[col + '_converted'].min()} to {df[col + '_converted'].max()}"
                    print(f"   📊 Date range: {date_range}")

                    # Show sample converted values
                    sample_converted = df[col + "_converted"].dropna().head(3).tolist()
                    print(f"   Sample converted values: {sample_converted}")

                date_info[col] = {
                    "original_dtype": str(df[col].dtype),
                    "converted_count": converted_count,
                    "total_non_null": df[col].notna().sum(),
                    "date_range": date_range if converted_count > 0 else None,
                }

            except Exception as e:
                print(f"   ❌ Conversion failed: {e}")
                date_info[col] = {"error": str(e)}

    return date_info


def explore_csv_file(file_path, expected_date_columns=None):
    """Comprehensive analysis of a single CSV file"""
    if expected_date_columns is None:
        expected_date_columns = []

    print(f"\n{'=' * 80}")
    print(f"📁 ANALYZING: {file_path.name}")
    print(f"{'=' * 80}")

    try:
        # Read the CSV
        df = pd.read_csv(file_path)

        # Basic info
        print(f"\n📊 BASIC INFORMATION:")
        print(f"   Rows: {len(df):,}")
        print(f"   Columns: {len(df.columns)}")
        print(f"   Total cells: {len(df) * len(df.columns):,}")

        # Column information
        print(f"\n📋 COLUMNS:")
        for i, col in enumerate(df.columns, 1):
            non_null_count = df[col].notna().sum()
            null_count = df[col].isna().sum()
            dtype = df[col].dtype
            print(
                f"   {i:2d}. {col:<25} | {str(dtype):<10} | {non_null_count:>5}/{len(df)} non-null ({null_count} null)"
            )

        # Data types summary
        print(f"\n🔍 DATA TYPES SUMMARY:")
        dtype_counts = df.dtypes.value_counts()
        for dtype, count in dtype_counts.items():
            print(f"   {str(dtype)}: {count} columns")

        # Missing data analysis
        print(f"\n❌ MISSING DATA:")
        missing_data = df.isnull().sum()
        if missing_data.sum() > 0:
            missing_percent = (missing_data / len(df) * 100).round(2)
            missing_summary = pd.DataFrame(
                {
                    "Column": missing_data.index,
                    "Missing Count": missing_data.values,
                    "Missing %": missing_percent.values,
                }
            )
            missing_summary = missing_summary[
                missing_summary["Missing Count"] > 0
            ].sort_values("Missing Count", ascending=False)

            for _, row in missing_summary.iterrows():
                print(
                    f"   {row['Column']:<25}: {row['Missing Count']:>4} ({row['Missing %']:>5.1f}%)"
                )
        else:
            print("   ✅ No missing data!")

        # Analyze date columns
        if expected_date_columns:
            analyze_dates(df, expected_date_columns)

        # Sample data
        print(f"\n📝 SAMPLE DATA (first 3 rows):")
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        print(df.head(3).to_string(index=False))

        # Unique values for small datasets or key columns
        print(f"\n🔑 UNIQUE VALUES ANALYSIS:")
        for col in df.columns:
            unique_count = df[col].nunique()
            total_count = len(df)

            if unique_count <= 20:  # Show all unique values for small sets
                unique_values = df[col].dropna().unique()
                print(f"   {col}: {unique_count} unique values")
                print(f"      Values: {list(unique_values)}")
            elif unique_count == total_count:  # Likely ID column
                print(
                    f"   {col}: {unique_count} unique values (appears to be unique identifier)"
                )
            else:
                print(f"   {col}: {unique_count} unique values")
                # Show most common values
                top_values = df[col].value_counts().head(3)
                print(f"      Top values: {dict(top_values)}")

        return df

    except Exception as e:
        print(f"❌ Error analyzing {file_path.name}: {e}")
        return None


def main():
    """Main exploration function"""
    print("🔍 ALANO CLUB CSV DATA EXPLORER")
    print("=" * 80)

    # Define CSV files and their expected date columns
    csv_files = {
        "2025_08_26_Members.csv": ["Milestone", "Date Joined"],
        "2025_08_26_MemberTypes.csv": [],
        "2025_08_26_Payments.csv": ["Date", "Card Exp. Date"],
        "2025_08_26_Payment Methods.csv": [],
        "2025_08_26_Friends.csv": [],
        "2025_08_26_Dead.csv": ["Milestone", "Date Joined", "Expires"],
        "2025_08_26_Frequency.csv": [],
    }

    data_dir = Path("csv_data")
    if not data_dir.exists():
        data_dir = Path("data/csv_data")

    if not data_dir.exists():
        print("❌ Could not find csv_data directory")
        return

    # Store all dataframes for summary
    dataframes = {}

    # Analyze each CSV file
    for filename, date_cols in csv_files.items():
        file_path = data_dir / filename
        if file_path.exists():
            df = explore_csv_file(file_path, date_cols)
            if df is not None:
                dataframes[filename] = df
        else:
            print(f"⚠️  File not found: {filename}")

    # Overall summary
    print(f"\n{'=' * 80}")
    print(f"📊 OVERALL DATA SUMMARY")
    print(f"{'=' * 80}")

    total_rows = sum(len(df) for df in dataframes.values())
    total_files = len(dataframes)

    print(f"\n📈 DATASET OVERVIEW:")
    print(f"   Total files analyzed: {total_files}")
    print(f"   Total records across all files: {total_rows:,}")

    print(f"\n📋 FILE SIZE SUMMARY:")
    for filename, df in dataframes.items():
        print(f"   {filename:<35}: {len(df):>6,} rows × {len(df.columns):>2} columns")

    # Key relationships
    print(f"\n🔗 KEY RELATIONSHIPS:")
    if "2025_08_26_Members.csv" in dataframes:
        members_df = dataframes["2025_08_26_Members.csv"]
        print(f"   Active members: {len(members_df):,}")

        if "2025_08_26_Dead.csv" in dataframes:
            dead_df = dataframes["2025_08_26_Dead.csv"]
            print(f"   Inactive/deceased members: {len(dead_df):,}")
            print(f"   Total member history: {len(members_df) + len(dead_df):,}")

        if "2025_08_26_Payments.csv" in dataframes:
            payments_df = dataframes["2025_08_26_Payments.csv"]
            print(f"   Payment records: {len(payments_df):,}")

            # Try to match payment member IDs with actual members
            try:
                member_ids = set(members_df["Member ID"].astype(str))
                payment_member_ids = set(payments_df["Member ID"].astype(str))
                matched_ids = member_ids.intersection(payment_member_ids)
                print(f"   Members with payment records: {len(matched_ids)}")
            except Exception as e:
                print(f"   Could not analyze member-payment relationship: {e}")


if __name__ == "__main__":
    main()
