Based on what you've outlined, here's what we need to do in the correct order:

## Current Status
✅ **COMPLETED**: Moved old management command scripts to archive folder

## Remaining Tasks (in order):

### **Step 1: Clean Database & Reset Migrations**
- **Goal**: Completely wipe existing database tables and reset migration history
- **Actions needed**:
  - **Drop/delete all existing database tables** (not just data, but the table structures themselves)
  - Delete all migration files in `members/migrations/` (except `__init__.py`)
  - Reset the database schema to completely clean state

#### **Commands to execute:**
```bash
# 1A. Drop all Django tables from database
python manage.py dbshell
# In PostgreSQL shell, run:
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
\q

# 1B. Delete migration files (keep __init__.py)
rm members/migrations/0*.py

rm -rf members/migrations/__pycache__

# 1C. Verify migrations are gone
ls members/migrations/

# 1D. Reset Django's migration tracking
python manage.py migrate --fake-initial
```

### **Step 2: Fix/Update Models** 
- **Goal**: Correct the models in `members/models.py` to match your cleaned data structure
- **Actions needed**:
  - Review current model definitions
  - Update field names, types, and relationships to match your 5 CSV files
  - Ensure models align with: members, payments, member_types, payment_methods, dead_members

#### **Commands to execute:**
```bash
# 2A. Backup current models (optional)
cp members/models.py members/models_backup.py

# 2B. Edit models to match CSV structure
# Update members/models.py to align with:
# - current_member_types.csv (member_type, member_dues, num_months)
# - current_payment_methods.csv (payment_method)
# - current_members.csv (member_id, first_name, last_name, etc.)
# - current_payments.csv (payment_amount, payment_date, receipt_number, etc.)
# - current_dead.csv (inactive members with same structure as members)

# 2C. Remove UUID system, use integer member_id that can rotate
# 2D. Update field names to match snake_case CSV columns
```

### **Step 3: Create Fresh Migrations**
- **Goal**: Generate new migrations based on updated models
- **Actions needed**:
  - Run `python manage.py makemigrations` 
  - Run `python manage.py migrate` to create clean database schema

#### **Commands to execute:**
```bash
# 3A. Generate initial migrations for updated models
python manage.py makemigrations

# 3B. Apply migrations to create new database schema
python manage.py migrate

# 3C. Verify tables were created correctly
python manage.py dbshell
# In PostgreSQL shell:
\dt
\q
```

### **Step 4: Create New Import Commands** 
- **Goal**: Build new management commands to import your cleaned CSV data
- **Actions needed**:
  - Create new import command(s) that work with the `/data/2025_09_02/cleaned/` files
  - Handle the 5 CSV files and their relationships properly

#### **Commands to execute:**
```bash
# 4A. Create new management command file
touch members/management/commands/import_cleaned_data.py

# 4B. Implement import logic for 5 CSV files:
# - Load member_types and payment_methods first (lookup tables)
# - Load current_members.csv 
# - Load current_dead.csv (for ID management)
# - Load current_payments.csv (references members)

# 4C. Test the import command
python manage.py import_cleaned_data

# 4D. Verify data was imported correctly
python manage.py shell
# Test queries to confirm data integrity
```
