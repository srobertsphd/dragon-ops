# Alano Club Member Management System

## Setup Instructions

### 1. Current Status
✅ Django project created  
✅ Member management models designed  
✅ Django Admin interface configured  
✅ Sample data script ready  
✅ SQLite database working locally  
✅ **Supabase PostgreSQL database connected**  
✅ **Testing framework (pytest) set up**  
✅ **Cursor configuration created**  
✅ **Database connectivity verified**  

### 2. Supabase Setup (✅ COMPLETED)

**Create Supabase Project:**
1. Go to [supabase.com](https://supabase.com)
2. Sign up with your email
3. Create new project (any name works, e.g. "Alano Club")
4. Choose a region (US West recommended)
5. Set a secure database password

**✅ Database Connection Configured:**
- **Project ID**: yspubhupkaokzqlxkgjk
- **Region**: East US (aws-1-us-east-1)
- **Connection Type**: Pooler (for external applications)
- **Format**: `postgresql://postgres.[project-id]:[password]@aws-1-[region].pooler.supabase.com:6543/postgres`

**✅ Environment Setup Complete:**
- `.env` file created with correct DATABASE_URL
- Connection tested and verified working
- PostgreSQL 17.4 confirmed

**Key Learning:** 
- Use **Connection Pooler** endpoint (`aws-1-us-east-1.pooler.supabase.com:6543`) for external apps
- Direct connection (`db.*.supabase.co:5432`) is for internal Supabase use only

### 3. Testing Framework (✅ COMPLETED)

**✅ Pytest Setup Complete:**
- Added pytest, pytest-django, pytest-cov using UV
- Created `tests/` directory with proper structure
- Database connectivity tests passing
- Configuration in `pytest.ini`

**Test Results:**
```bash
# Run database connection test
pytest tests/test_database.py -v -s

# Results: ✅ PASSED
# - Connection to Supabase confirmed
# - PostgreSQL 17.4 verified
# - Database queries working
```

### 4. Development Environment (✅ COMPLETED)

**✅ Cursor Configuration:**
- Created `.cursor/rules/project-context.mdc`
- Project context for UV, Django, Supabase
- Development workflow preferences documented

### 5. Next Steps - Database Migration

**Ready to proceed:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Migrate to Supabase
python manage.py migrate

# Create superuser for Supabase
python manage.py createsuperuser

# Load sample data
python setup_sample_data.py
```

### 6. Running the Application

```bash
# Start development server
python manage.py runserver

# Access the admin interface
# http://127.0.0.1:8000/admin/
```

### 7. Admin Interface Features

**Member Management:**
- Add/Edit/Delete members
- Organized form sections (Personal, Contact, Work, Membership)
- Search by name, ID, phone, city
- Filter by membership type, status, state
- Bulk actions (activate, deactivate, mark deceased)

**Payment Tracking:**
- Record member payments
- Track payment methods
- Period coverage tracking
- Payment history per member

**Member Types & Payment Methods:**
- Configure membership categories
- Set up payment options
- Manage dues structure

### 8. Excel Data Import

Your existing Excel files have been organized in the `data/` directory:
- `data/xlsx_data/` - Original Excel files
- `data/csv_data/` - Converted CSV files for processing

**Convert Excel to CSV:**
```bash
# From project root
python data/convert_xlsx_to_csv.py

# Or from data directory
cd data && python convert_xlsx_to_csv.py
```

**Available data files:**
- `2025_08_26_Members.csv` → 325 member records
- `2025_08_26_MemberTypes.csv` → Membership categories  
- `2025_08_26_Payments.csv` → 1,337 payment records
- `2025_08_26_Payment Methods.csv` → Payment options
- `2025_08_26_Friends.csv` → 60 member connections
- `2025_08_26_Dead.csv` → 1,400 historical records
- `2025_08_26_Frequency.csv` → Frequency data

Import script can be created once data structure is confirmed.

### 9. Deployment to Render

**Ready for deployment:**
- Requirements.txt configured
- WhiteNoise for static files
- Environment variable support
- PostgreSQL optimized

**Deploy steps:**
1. Push code to GitHub
2. Connect Render to repository
3. Add environment variables in Render dashboard
4. Deploy!

### 10. Account Transfer

When ready to transfer to organization:
1. **Supabase:** Use project transfer feature
2. **Render:** Transfer project ownership
3. **GitHub:** Transfer repository ownership

### 11. Login Credentials

**Current superuser:**
- Username: `admin`
- Password: `[set during createsuperuser]`
- URL: `http://127.0.0.1:8000/admin/`

### 12. Database Architecture - Member ID Management

**CRITICAL IMPLEMENTATION DECISION:** The club requires member IDs to be recyclable (1-1000 range) while maintaining data integrity and supporting member reinstatement.

#### **Solution: Modified Dual Key System**

**Core Principle:** Separate permanent database identity from recyclable display ID.

```python
class Member:
    member_uuid = UUIDField(primary_key=True)  # PERMANENT ID - never changes
    member_id = IntegerField(null=True)        # CURRENT display ID (1-1000, recyclable)
    preferred_member_id = IntegerField()       # PREFERRED ID for reinstatement
    status = CharField(choices=['active', 'inactive', 'deceased'])
    first_name = CharField()
    last_name = CharField()
    date_joined = DateField()
    date_inactivated = DateField(null=True)
    
class Payment:
    member = ForeignKey(Member, on_delete=PROTECT)  # Links to UUID, not member_id
    amount = DecimalField()
    date = DateField()
```

#### **Key Business Rules:**

1. **Member Creation:**
   - Gets next available member_id (1-1000)
   - preferred_member_id = member_id (remember their "home" ID)
   - status = 'active'

2. **Member Inactivation:**
   - status = 'inactive'
   - member_id = None (frees up display ID for recycling)
   - date_inactivated = today()

3. **Member Reinstatement:**
   - Try to restore preferred_member_id if available
   - Otherwise assign next available ID
   - status = 'active'

4. **Payment Tracking:**
   - Always links to member_uuid (permanent)
   - Payment history preserved regardless of ID changes

#### **Reinstatement Logic:**

```python
def reinstate_member(member_uuid):
    member = Member.objects.get(member_uuid=member_uuid)
    
    # Try to get their preferred ID back
    if is_member_id_available(member.preferred_member_id):
        member.member_id = member.preferred_member_id
        print(f"✅ Reinstated with original ID #{member.preferred_member_id}")
    else:
        member.member_id = get_next_available_member_id()
        print(f"⚠️ Reinstated with new ID #{member.member_id}")
    
    member.status = 'active'
    member.date_inactivated = None
    member.save()
```

#### **Benefits:**
- ✅ Payment history never breaks (UUID-based)
- ✅ Preferred IDs automatically attempted on reinstatement
- ✅ Clean ID recycling (1-1000 range maintained)
- ✅ Simple staff workflow (one-click reinstatement)
- ✅ Graceful conflict resolution when preferred ID taken

#### **Implementation Notes:**
- Frequency table identified as unused/orphaned - excluded from implementation
- Member ID conflicts handled with user-friendly options
- All foreign keys use UUID for stability
- Display ID separate from database relationships

### 13. Django Models Implementation

#### **Member Table Structure**

**Purpose:** Core member information with dual key system and stored expiration tracking.

```python
class Member:
    # Identity fields (dual key system)
    member_uuid = UUIDField(primary_key=True)           # PERMANENT ID - never changes
    member_id = IntegerField(null=True, unique=True)    # Display ID (1-1000, recyclable)
    preferred_member_id = IntegerField()                # Preferred ID for reinstatement
    
    # Basic information (required)
    first_name = CharField(max_length=50)               # Required field
    last_name = CharField(max_length=50)                # Required field
    email = EmailField(blank=True)                      # Optional, primary contact
    
    # Membership information
    member_type = ForeignKey('MemberType', on_delete=PROTECT)  # Link to MemberType table
    status = CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'), 
        ('deceased', 'Deceased')
    ])
    expiration_date = DateField()                       # Current membership expires (stored, not calculated)
    
    # Important dates
    milestone_date = DateField()                        # Sobriety date (for anonymity)
    date_joined = DateField()                          # Club membership start date
    date_inactivated = DateField(null=True, blank=True)  # When member went inactive
    
    # Contact information (optional)
    home_address = TextField(blank=True)                # Residential/mailing address
    home_country = CharField(max_length=50, blank=True, default='US')  # Country of residence
    home_phone = CharField(max_length=20, blank=True)   # Primary phone number
    
    # Note: SerialNum field removed - identified as unused legacy data
```

#### **MemberType Table Structure**

**Purpose:** Defines membership categories with associated dues and coverage rules.

```python
class MemberType:
    id = AutoField(primary_key=True)
    name = CharField(max_length=50, unique=True)        # "Regular", "Senior", "Life", etc.
    monthly_dues = DecimalField(max_digits=8, decimal_places=2)  # Monthly dues amount
    coverage_months = DecimalField(max_digits=5, decimal_places=1)  # Period coverage (1.0=monthly, 12.0=annual, 300.0=lifetime)
    description = TextField(blank=True)                 # Optional details about membership type
    is_active = BooleanField(default=True)             # Can disable member types
    
    def __str__(self):
        return f"{self.name} (${self.monthly_dues}/month)"
```

#### **Initial MemberType Data**

Based on existing CSV data, populate with these membership categories:

| ID | Name | Monthly Dues | Coverage Months | Description |
|----|------|--------------|-----------------|-------------|
| 2 | Couple | $40.00 | 1.0 | Joint membership for couples |
| 3 | FarAway Friends | $20.00 | 1.0 | Reduced rate for distant members |
| 4 | Fixed/Income | $20.00 | 1.0 | Financial assistance rate |
| 5 | 500 Club | $500.00 | 12.0 | Annual donor level membership |
| 6 | Reinstate | $25.00 | 1.0 | Returning member rate |
| 7 | Honorary | $0.00 | 1.0 | No dues required |
| 8 | Life | $3000.00 | 300.0 | Lifetime membership (never expires) |
| 9 | Regular | $30.00 | 1.0 | Standard membership |
| 10 | Senior | $20.00 | 1.0 | Age-based discount |

#### **Key Field Changes from Original Data**
- **Removed:** `SerialNum` (unused legacy field)
- **Added:** `expiration_date` (stored membership expiration)
- **Added:** `member_type` (foreign key to MemberType table)
- **Added:** `status` (active/inactive/deceased)
- **Added:** Dual key system fields (`member_uuid`, `preferred_member_id`)

#### **Payment Processing Logic**
When payments are entered:
1. **Auto-calculate suggested expiration** based on payment amount and member type
2. **Allow staff override** of calculated expiration date
3. **Update member.expiration_date** when payment is saved
4. **Maintain audit trail** in Payment table

### 14. Next Steps

1. ✅ **Set up Supabase account** (COMPLETED)
2. ✅ **Database connection verified** (COMPLETED)
3. ✅ **Database architecture designed** (Dual key system documented)
4. ✅ **Django models designed** (Member and MemberType structures documented)
5. **Create Django models in members/models.py**
6. **Run Django migrations to Supabase**
7. **Populate initial MemberType data**
8. **Create Payment and PaymentMethod models**
9. **Test member management interface**
10. **Import existing CSV data** 
11. **Deploy to Render**
12. **Train organization users**

## Support

The Django Admin interface provides:
- Form-based member entry (like your screenshot)
- Search and filtering
- Payment tracking
- Data export capabilities
- User permissions management

This replaces complex desktop applications with a simple web interface accessible from any device.
