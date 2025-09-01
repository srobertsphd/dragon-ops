# Alano Club Data Structure Documentation

## Overview
This document describes the structure and content of the Alano Club member management data exported on August 26, 2025. The data consists of 7 CSV files representing different aspects of club operations.

## CSV Files Summary

| File | Purpose | Records | Key Relationships |
|------|---------|---------|-------------------|
| `2025_08_26_Members.csv` | Active club members | ~325 | Primary member data |
| `2025_08_26_MemberTypes.csv` | Membership categories | ~10 | Referenced by Members |
| `2025_08_26_Payments.csv` | Payment history | ~1,337 | Links to Members |
| `2025_08_26_Payment Methods.csv` | Payment options | ~11 | Referenced by Payments |
| `2025_08_26_Friends.csv` | External contacts | ~60 | Separate from members |
| `2025_08_26_Dead.csv` | Inactive/deceased members | ~1,400 | Historical member data |
| `2025_08_26_Frequency.csv` | Payment frequencies | ~6 | Referenced by other tables |

---

## 1. Members Table (`2025_08_26_Members.csv`)

**Purpose:** Active club members and their core information

### Fields Description

| Field | Type | Description | Business Rules |
|-------|------|-------------|----------------|
| **Member ID** | Integer | Unique member identifier (1-1000) | - Sequential numbering system<br>- Numbers recycled when members become inactive<br>- New members get next available number |
| **First Name** | Text | Member's first name | - Required field |
| **Last Name** | Text | Member's last name | - Required field |
| **E Mail Name** | Text | Email address | - Optional<br>- Primary contact method |
| **Milestone** | Date | Sobriety date | - Called "milestone" for anonymity<br>- Format: YYYY-MM-DD<br>- Critical for anniversary tracking |
| **Date Joined** | Date | Club membership start date | - Format: YYYY-MM-DD<br>- May differ from milestone date |
| **SerialNum** | Text | Unknown legacy field | - Purpose unclear<br>- May be deprecated |
| **Home Address** | Text | Residential address | - Optional<br>- Mailing address |
| **Home Country** | Text | Country of residence | - Optional<br>- Mostly US members |
| **Home Phone** | Text | Primary phone number | - Format: (XXX) XXX-XXXX<br>- Optional |

### Data Quality Notes
- ~325 active members
- Member ID recycling creates management complexity
- Some legacy data inconsistencies expected
- Email addresses not available for all members

---

## 2. Member Types Table (`2025_08_26_MemberTypes.csv`)

**Purpose:** Defines membership categories and associated dues structure

### Fields Description

| Field | Type | Description | Business Rules |
|-------|------|-------------|----------------|
| **MemberTypeID** | Integer | Unique category identifier | - Primary key |
| **MemberType** | Text | Membership category name | - Descriptive name |
| **Member Dues** | Decimal | Monthly dues amount | - In USD<br>- 0.00 for honorary members |
| **NumMonths** | Decimal | Payment period coverage | - 1.0 = monthly<br>- 12.0 = annual<br>- 300.0 = lifetime |

### Current Membership Types

| ID | Type | Monthly Dues | Period | Notes |
|----|------|--------------|---------|-------|
| 2 | Couple | $40.00 | Monthly | Joint membership |
| 3 | FarAway Friends | $20.00 | Monthly | Remote members |
| 4 | Fixed/Income | $20.00 | Monthly | Reduced rate |
| 5 | 500 Club | $500.00 | Annual | Major donor tier |
| 6 | Reinstate | $25.00 | Monthly | Returning members |
| 7 | Honorary | $0.00 | Monthly | No dues required |
| 8 | Life | $3000.00 | Lifetime | One-time payment |
| 9 | Regular | $30.00 | Monthly | Standard membership |
| 10 | Senior | $20.00 | Monthly | Age-based discount |

---

## 3. Payments Table (`2025_08_26_Payments.csv`)

**Purpose:** Complete payment transaction history

### Fields Description

| Field | Type | Description | Business Rules |
|-------|------|-------------|----------------|
| **Payment ID** | Integer | Unique transaction identifier | - Primary key |
| **Member ID** | Text/Integer | Reference to member | - Links to Members table<br>- Some entries show names instead of IDs |
| **Amount** | Decimal | Payment amount in USD | - Positive values only |
| **Date** | Date | Transaction date | - Format varies (M/D/YYYY) |
| **Credit Card #** | Text | Card number (if applicable) | - Mostly empty for privacy |
| **Cardholder Name** | Text | Name on card | - Mostly empty |
| **Card Exp. Date** | Date | Card expiration | - Rarely populated |
| **PaymentMethodID** | Text | Payment method used | - References Payment Methods table |
| **Receipt No.** | Decimal | Receipt number | - Sequential numbering |

### Data Quality Issues
- Member ID field contains both IDs and names (data inconsistency)
- Date formats vary throughout the dataset
- ~1,337 payment records total
- Most payments are cash-based

---

## 4. Payment Methods Table (`2025_08_26_Payment Methods.csv`)

**Purpose:** Defines available payment options

### Fields Description

| Field | Type | Description |
|-------|------|-------------|
| **PaymentMethodID** | Integer | Unique method identifier |
| **PaymentMethod** | Text | Payment method name |
| **Credit Card?** | Boolean | Whether method involves credit cards |

### Available Methods

| ID | Method | Credit Card? | Usage Notes |
|----|--------|--------------|-------------|
| 1 | Other | No | Miscellaneous payments |
| 2 | Cash | No | Most common method |
| 3 | Check | No | Traditional payment |
| 4 | Life | No | Lifetime membership payment |
| 5 | Work | No | Workplace deduction |
| 6 | Board Elect | No | Board-elected payment |
| 7 | Partial Payment | No | Split payments |
| 8 | Venmo | No | Digital payment |
| 9 | PayPal | No | Digital payment |
| 10 | Zelle | No | Digital payment |
| 11 | Work | No | Duplicate entry (data issue) |

---

## 5. Friends Table (`2025_08_26_Friends.csv`)

**Purpose:** External contacts and affiliated organizations

### Fields Description

| Field | Type | Description |
|-------|------|-------------|
| **FriendID** | Integer | Unique contact identifier |
| **Member ID** | Decimal | Associated member (if any) |
| **First Name** | Text | Contact first name |
| **Last Name** | Text | Contact last name |
| **Member Type** | Text | Relationship type |
| **Company** | Text | Organization name |
| **Title** | Text | Contact's job title |
| **Work Address** | Text | Business address |
| **Work City** | Text | Business city |
| **Work State** | Text | Business state |
| **Zip Code** | Text | Business zip code |
| **Work Phone** | Text | Business phone |
| **Home Phone** | Text | Personal phone |
| **E Mail Name** | Text | Email address |
| **Fax** | Text | Fax number (legacy) |

### Purpose
- External organization contacts
- Community partners
- Service providers
- Honorary members
- ~60 contacts total

---

## 6. Dead Table (`2025_08_26_Dead.csv`)

**Purpose:** Historical records of inactive and deceased members

### Fields Description

| Field | Type | Description | Business Rules |
|-------|------|-------------|----------------|
| **DeadID** | Integer | Unique historical record ID | - Primary key |
| **MemberID** | Decimal | Original member ID | - May be null for older records |
| **First Name** | Text | Member's first name | - Historical data |
| **Last Name** | Text | Member's last name | - Historical data |
| **Member Type** | Text | Last membership type | - Historical reference |
| **Home Address** | Text | Last known address | - Historical data |
| **Home City** | Text | Last known city | - Historical data |
| **Home State** | Text | Last known state | - Historical data |
| **Home Zip** | Text | Last known zip code | - Historical data |
| **Home Phone** | Text | Last known phone | - Historical data |
| **E Mail Name** | Text | Last known email | - Historical data |
| **Milestone** | Date | Sobriety date | - Historical milestone |
| **Date Joined** | Date | Original join date | - Historical data |
| **Expires** | Date | Membership expiration | - Last payment coverage end |
| **Payment Method** | Text | Last payment method used | - Historical reference |

### Purpose
- Preserve member history
- Track membership lifecycle
- Enable Member ID recycling
- Memorial purposes
- ~1,400 historical records

---

## 7. Frequency Table (`2025_08_26_Frequency.csv`)

**Purpose:** Defines payment frequency options

### Fields Description

| Field | Type | Description |
|-------|------|-------------|
| **FreqID** | Integer | Unique frequency identifier |
| **Frequency** | Text | Frequency description |

### Available Frequencies

| ID | Frequency | Usage |
|----|-----------|-------|
| 1 | Weekly | Weekly payments |
| 2 | Monthly | Most common |
| 3 | Semi-Annually | Twice yearly |
| 4 | Annually | Yearly payments |
| 5 | Adhoc | As-needed basis |
| 6 | Daily | Daily payments (rare) |

---

## Data Relationships

```
Members (1) ←→ (M) Payments
Members (M) ←→ (1) MemberTypes  
Payments (M) ←→ (1) PaymentMethods
Dead (historical Members)
Friends (independent contacts)
Frequency (reference data)
```

## Implementation Notes

### Member ID Management
- **Challenge:** Recycling member IDs when members become inactive
- **Solution:** Move inactive members to Dead table, free up ID for reuse
- **Complexity:** Requires careful audit trail and validation

### Date Handling
- **Issue:** Multiple date formats in source data
- **Required:** Standardize to YYYY-MM-DD format
- **Fields affected:** Milestone, Date Joined, Payment dates, Expiration dates

### Data Quality Issues
1. **Payment table:** Member ID field contains names in some records
2. **Duplicate payment methods:** "Work" appears twice with different IDs
3. **Inconsistent date formats:** Need standardization
4. **Missing data:** Not all fields populated for all records

### Migration Strategy
1. **Clean and validate** all data before import
2. **Standardize date formats** across all tables
3. **Resolve Member ID inconsistencies** in payments
4. **Implement ID recycling logic** with proper audit trail
5. **Preserve historical data** integrity during migration