#!/usr/bin/env python
"""
Convert all Excel files in xlsx_data directory to CSV files.
Creates a new 'csv_data' directory with the converted files.

Usage: python convert_xlsx_to_csv.py
"""

import os
import pandas as pd
from pathlib import Path
import sys


def convert_xlsx_to_csv():
    """Convert all .xlsx files in xlsx_data directory to CSV format."""

    # Handle running from either project root or data directory
    current_dir = Path.cwd()

    if current_dir.name == "data":
        # Running from data directory
        xlsx_dir = Path("xlsx_data")
        csv_dir = Path("csv_data")
    elif (current_dir / "data").exists():
        # Running from project root
        xlsx_dir = Path("data/xlsx_data")
        csv_dir = Path("data/csv_data")
    else:
        # Try to find data directory
        data_dir = Path(__file__).parent
        xlsx_dir = data_dir / "xlsx_data"
        csv_dir = data_dir / "csv_data"

    # Check if xlsx_data directory exists
    if not xlsx_dir.exists():
        print(f"❌ Error: {xlsx_dir} directory not found!")
        return False

    # Create csv_data directory if it doesn't exist
    csv_dir.mkdir(exist_ok=True)
    print(f"📁 Created/Using directory: {csv_dir}")

    # Find all .xlsx files
    xlsx_files = list(xlsx_dir.glob("*.xlsx"))

    if not xlsx_files:
        print(f"❌ No .xlsx files found in {xlsx_dir}")
        return False

    print(f"📊 Found {len(xlsx_files)} Excel files to convert:")

    converted_count = 0
    error_count = 0

    for xlsx_file in xlsx_files:
        try:
            print(f"\n🔄 Converting: {xlsx_file.name}")

            # Read Excel file
            # Try to read all sheets, but if there are multiple sheets, read the first one
            excel_data = pd.read_excel(xlsx_file, sheet_name=None)  # Read all sheets

            if isinstance(excel_data, dict):
                # Multiple sheets - process each sheet
                if len(excel_data) == 1:
                    # Only one sheet, use it
                    sheet_name, df = next(iter(excel_data.items()))
                    csv_filename = xlsx_file.stem + ".csv"
                    csv_path = csv_dir / csv_filename

                    df.to_csv(csv_path, index=False)
                    print(
                        f"   ✅ Saved: {csv_filename} ({len(df)} rows, {len(df.columns)} columns)"
                    )
                    converted_count += 1

                else:
                    # Multiple sheets - save each sheet separately
                    for sheet_name, df in excel_data.items():
                        csv_filename = f"{xlsx_file.stem}_{sheet_name}.csv"
                        csv_path = csv_dir / csv_filename

                        df.to_csv(csv_path, index=False)
                        print(
                            f"   ✅ Saved: {csv_filename} ({len(df)} rows, {len(df.columns)} columns)"
                        )
                        converted_count += 1
            else:
                # Single sheet
                csv_filename = xlsx_file.stem + ".csv"
                csv_path = csv_dir / csv_filename

                excel_data.to_csv(csv_path, index=False)
                print(
                    f"   ✅ Saved: {csv_filename} ({len(excel_data)} rows, {len(excel_data.columns)} columns)"
                )
                converted_count += 1

        except Exception as e:
            print(f"   ❌ Error converting {xlsx_file.name}: {e}")
            error_count += 1

    # Summary
    print(f"\n📈 Conversion Summary:")
    print(f"   ✅ Successfully converted: {converted_count} files")
    if error_count > 0:
        print(f"   ❌ Errors: {error_count} files")

    print(f"\n📂 CSV files saved in: {csv_dir.absolute()}")

    # List the created CSV files
    csv_files = list(csv_dir.glob("*.csv"))
    if csv_files:
        print(f"\n📋 Created CSV files:")
        for csv_file in sorted(csv_files):
            file_size = csv_file.stat().st_size
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            print(f"   • {csv_file.name} ({size_str})")

    return converted_count > 0


def main():
    print("🔄 Excel to CSV Converter for Alano Club Data")
    print("=" * 50)

    success = convert_xlsx_to_csv()

    if success:
        print("\n🎉 Conversion completed successfully!")
        print("\nNext steps:")
        print("1. Review the CSV files in the csv_data directory")
        print("2. Use these CSV files for data import scripts")
        print("3. Verify the data looks correct before importing to Django")
    else:
        print("\n❌ Conversion failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
