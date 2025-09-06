# Data Processing Summary

## Members Data Processing

### Data Source
- **File**: `data/2025_09_02/excel_files/2025_09_02_Members-Data.xlsx`
- **Read using**: pandas `read_excel()`

### Data Transformations
1. **Date Conversion**: Converted `Date Joined`, `Milestone`, and `Expires` columns to datetime format using `pd.to_datetime()` with `errors='coerce'` to handle invalid dates
2. **Lifetime Members**: Set expiration date to `2099-12-31` for all members with `Member Type = 'life'` (PostgreSQL-compatible approach for non-nullable date field)
3. **Member Type Corrections**: Reassigned 5 members from "Reinstate" or NaN member types to "Regular":
   - Ken Beasley
   - Robert Gutierrez  
   - Kiven Christine
   - James Long
   - Bill Burke
   
   *Note: These reassignments will be validated during payment processing*

4. **Column Renaming**: Applied code-friendly column names using snake_case:
   - `Member ID` → `member_id`
   - `First Name` → `first_name`
   - `Last Name` → `last_name`
   - `Member Type` → `member_type`
   - `Home Address` → `home_address`
   - `Home City` → `home_city`
   - `Home State` → `home_state`
   - `Home Zip` → `home_zip`
   - `Home Phone` → `home_phone`
   - `E Mail Name` → `email`
   - `Date Joined` → `date_joined`
   - `Milestone` → `milestone_date`
   - `Expires` → `expiration_date`

5. **Home Zip Code Cleaning**: Standardized zip codes to 5-digit format by removing hyphens and extensions (e.g., `95070-    ` → `95070`, `95131-2760` → `95131`)

6. **Home State Standardization**: Mapped all state values to proper 2-letter uppercase abbreviations:
   - **CA variations**: `Ca`, `CA.`, `ca` → `CA`
   - **Other corrections**: `Il` → `IL`, `Tn` → `TN`, `Id` → `ID`, `Mn` → `MN`, `HW` → `HI`
   - **Final valid states**: CA, NY, NV, GA, PA, LA, AZ, WA, IL, TN, ID, MN, HI
   - **Missing data**: 6 records with NaN values

7. **Phone Number Validation**: Verified all 303 phone numbers follow the standard format `(XXX) XXX-XXXX` with proper parentheses, space, and hyphen formatting

### Current Dataset State
- **Total Records**: 335 members (RangeIndex: 0 to 334)
- **Total Columns**: 13
- **Data Completeness**:
  - `member_id`: 335 non-null (100%)
  - `first_name`: 335 non-null (100%)
  - `last_name`: 335 non-null (100%)
  - `member_type`: 335 non-null (100%)
  - `home_address`: 322 non-null (96.1%)
  - `home_city`: 329 non-null (98.2%)
  - `home_state`: 329 non-null (98.2%)
  - `home_zip`: 317 non-null (94.6%)
  - `home_phone`: 303 non-null (90.4%)
  - `email`: 300 non-null (89.6%)
  - `date_joined`: 333 non-null (99.4%)
  - `milestone_date`: 311 non-null (92.8%)
  - `expiration_date`: 334 non-null (99.7%)
- **Data Types**: 3 datetime64[ns], 1 int64, 9 object
- **Memory Usage**: 34.2+ KB

### Data Analysis
- **Total expired members** (excluding lifetime): 91
- **Analysis**: Checked expired members to identify those expired more than 3 months ago vs. recently expired

## Member Types Reference

| member_type     | member_dues | num_months | count |
|----------------|-------------|------------|-------|
| Couple         | 40.0        | 1        | 26    |
| FarAway Friends| 20.0        | 1        | 14    |
| Fixed/Income   | 20.0        | 1        | 93    |
| 500 Club       | 500.0       | 12       | 0     |
| Honorary       | 0.0         | 1        | 0     |
| Life           | 3000.0      | 300      | 43    |
| Regular        | 30.0        | 1        | 49    |
| Senior         | 20.0        | 1        | 110   |

*Note: Life membership duration is 300 months (25 years)*

## Member Payments Data Processing

### Data Source
- **File**: `data/2025_09_02/excel_files/2025_09_02_Member Payments.xlsx`
- **Read using**: pandas `read_excel()`

### Data Transformations

1. **Column Removal**: Dropped 25 unnecessary columns including:
   - **Credit card data**: `Credit Card #`, `Cardholder Name`, `Card Exp. Date`
   - **Work-related fields**: `Company`, `Title`, `Work Address`, `Work City`, `Work State`, `Area Code`, `Zip Code`, `Work County`, `Work Phone`, `Extension`
   - **System fields**: `Selected`, `Barcode ID`, `SRVTypID`, `MailerID`, `SerialNum`, `Payment ID`, `Member ID.1`
   - **Other fields**: `Send to Work?`, `Fax`, `Due Amount`, `Payment Method`, `Home Country`

2. **Column Renaming**: Applied code-friendly column names using snake_case:
   - `Member ID` → `member_id`
   - `First Name` → `first_name`
   - `Last Name` → `last_name`
   - `Member Type` → `member_type`
   - `Home Address` → `home_address`
   - `Home City` → `home_city`
   - `Home State` → `home_state`
   - `Home Zip` → `home_zip`
   - `Home Phone` → `home_phone`
   - `E Mail Name` → `email`
   - `Date Joined` → `date_joined`
   - `Milestone` → `milestone_date`
   - `Expires` → `expiration_date`
   - `Date` → `payment_date`
   - `Payments.PaymentMethodID` → `payment_method`
   - `Reciept No.` → `receipt_number`
   - `Amount` → `payment_amount`
   - `Mobile` → `mobile_phone`

3. **Date Conversion**: Converted date columns to datetime format using `pd.to_datetime()` with `errors='coerce'`:
   - `date_joined`, `milestone_date`, `expiration_date`, `payment_date`

4. **Member Validation**: Verified all payment records correspond to existing members in the members dataset

5. **Data Quality Cleaning**:
   - **Dropped missing payment methods**: Removed 1 record with null `payment_method`
   - **Dropped missing payment amounts**: Removed 2 records with null `payment_amount`
   - **Mobile phone retention**: Kept `mobile_phone` column (6 records) for future merging with member structure

### Current Payments Dataset State (After Cleaning)
- **Total Records**: 722 payment entries (cleaned from original 725)
- **Total Columns**: 18
- **Records Removed**: 3 total (1 missing payment method + 2 missing payment amounts)
- **Data Completeness**: All payment records now have complete `payment_method` and `payment_amount` data
- **Data Types**: 4 datetime64[ns], 2 float64, 1 int64, 11 object
- **Key Fields**:
  - `member_id`: 722 non-null (100%)
  - `payment_amount`: 722 non-null (100%)
  - `payment_date`: ~720 non-null (~99.7%)
  - `payment_method`: 722 non-null (100%)
  - `receipt_number`: ~720 non-null (~99.7%)
  - `mobile_phone`: 6 non-null (0.8%)

## Dead Members Data Processing

### Data Source
- **File**: `data/2025_09_02/excel_files/2025_08_26_Dead.xlsx`
- **Read using**: pandas `read_excel()`

### Data Transformations

1. **Column Renaming**: Applied code-friendly column names using snake_case to match established conventions:
   - `DeadID` → `dead_id`, `MemberID` → `member_id`, `First Name` → `first_name`, etc.

2. **Column Removal**: Dropped unnecessary columns:
   - `dead_id` (internal ID not needed for analysis)
   - `payment_method` (minimal data, only 5 non-null values)

3. **Duplicate Handling**: Removed duplicate name combinations by keeping records with most recent expiration dates:
   - **Found**: 120 duplicate records across 54 unique name combinations
   - **Kept**: Most recent expiration date for each duplicate name
   - **Final count**: 1,346 unique members (reduced from 1,400)

4. **State Standardization**: Mapped state values to proper 2-letter uppercase abbreviations:
   - `Ca` → `CA`, `Az` → `AZ`, `Or` → `OR`, `Wy` → `WY`, `nebr` → `NE`, `Utah` → `UT`
   - Removed 1 record with invalid state value (`\`)

5. **Phone Number Standardization**: Corrected 121 phone numbers to `(XXX) XXX-XXXX` format:
   - **Raw digits**: `4084215602` → `(408) 421-5602`
   - **Malformed area codes**: `(6) 692-7293` → `(408) 692-7293`

6. **Zip Code Cleaning**: Standardized to 5-digit format by removing hyphens and extensions

7. **Data Type Conversion**: Converted `member_id` to nullable integer type (`Int64`)

### Current Dead Members Dataset State
- **Total Records**: 1,346 deceased members (cleaned from original 1,400)
- **Total Columns**: 13
- **Records Removed**: 54 total (duplicate names with older expiration dates)
- **Data Quality**: Standardized phone numbers, state abbreviations, and zip codes
- **Output File**: `data/current_dead.csv`

### Notes
- Datetime format preserved for PostgreSQL compatibility
- Date formatting will be handled at the PostgreSQL display layer
