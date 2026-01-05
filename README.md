# Dragon Ops
## Durable Records and Accounting General Operations Nexus

A Django-based web application for managing records, payments, and organizational data. Dragon Ops provides a professional, secure platform for durable record-keeping and accounting operations.

## Features

- **Member Management**: Add, edit, and view records with detailed contact information and automatic ID recycling
- **Payment Tracking**: Record and track payments with automatic expiration date management and complete payment history
- **Member Types**: Configure different membership categories and payment methods
- **Search & Reporting**: Powerful search capabilities and comprehensive reporting tools
- **Data Security**: Secure PostgreSQL database with comprehensive backup and audit capabilities
- **Admin Interface**: Full administrative control via Django Admin
- **Data Import**: Tools for importing existing Excel/CSV data
- **Modern UI**: Bootstrap-styled forms and interfaces with responsive design
- **Deployment Ready**: Configured for deployment on Render with environment-based configuration

## Report Generation

Dragon Ops includes a comprehensive suite of reporting tools for data analysis, exports, and member management:

- **Current Members Report**: View all active members with their payment history. Supports sorting by name or ID, separates regular and life members, and includes PDF download capability.
- **Recent Payments Report**: View all payments from the last year (365 days) with detailed payment information. Export to CSV format for accounting and record-keeping.
- **Newsletter Export**: Generate Excel file with active member data formatted for newsletter distribution. Includes member contact information and membership details.
- **New Member Export**: Export new members (active members who joined within a selected date range) to Excel. Customizable date range selection with validation (up to 6 months).
- **Milestone Export**: Export active members whose milestone dates (anniversaries) fall within a selected date range to Excel. Useful for recognizing member anniversaries and special occasions.
- **Expires Two Months Export**: Export active members whose expiration dates are 60+ days ago (expired 2+ months ago) to Excel. Helps identify members who need renewal reminders.
- **Deactivate Expired Members**: Review and deactivate members expired 90+ days with no payment after expiration. Interactive interface with member selection and bulk deactivation capabilities.
- **Database Backup**: Create and download database backup files. Includes database type and timestamp in filename for easy version tracking.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database (or use Supabase)
- UV package manager

### Installation

1. **Install UV** (if not already installed):  
   
   **macOS and Linux:**  
   ``` bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
      
   After installation, restart your terminal or run:
   ``` bash
   source $HOME/.cargo/env
   ```

      For alternative installation methods, see the [UV installation guide](https://docs.astral.sh/uv/getting-started/installation/).

2. **Create virtual environment:**
   ``` bash
   uv venv
   ```
   3. **Activate virtual environment:**
   ``` bash
   source .venv/bin/activate
   ```
   
4. **Install dependencies:**
   ``` bash
   uv sync
   ```
   5. **Configure environment variables:**
   
   Create a `.env` file in the project root with:
   ``` python
   DATABASE_URL=your_postgresql_connection_string
   SECRET_KEY=your_django_secret_key
   DEBUG=True
   ```
   6. **Run migrations:**
   ``` bash
   python manage.py migrate
   ```
   7. **Create superuser (optional):**  
   ``` bash
   python manage.py createsuperuser
   ```
   8. **Run development server:**
   ``` bash
   python manage.py runserver 8001
   ```
   9. **Access the application:**
   - Web interface: http://127.0.0.1:8001/
   - Admin interface: http://127.0.0.1:8001/admin/

## Deployment on Render

Dragon Ops is configured for deployment on Render using the included `render.yaml` configuration file.

### Deployment Steps

1. **Connect your repository** to Render
2. **Configure environment variables** in Render dashboard:
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `SECRET_KEY`: Django secret key (generate a secure random string)
   - `DEBUG`: Set to `False` for production
3. **Deploy**: Render will automatically detect the `render.yaml` and deploy the application

The application will be automatically built and deployed on every push to the main branch.

## Data Management

The system includes ETL scripts for cleaning and transforming data. See [`scripts/DATA_PREP_DESCRIPTION.md`](scripts/DATA_PREP_DESCRIPTION.md) for detailed information about the transformation scripts and data processing steps.

**Run the transformation scripts:**  (From the project root directory  )

``` bash
python scripts/clean_member_data.py  
python scripts/clean_dead_data.py  
python scripts/clean_member_payments.py## Testing  
```

For automated testing, see `tests/README.md`.  

For comprehensive manual testing instructions, see [TESTING_GUIDE.md](docs/TESTING_GUIDE.md).  

## Technology Stack

- **Framework**: Django 4.2+
- **Database**: PostgreSQL (via Supabase)
- **Package Manager**: UV
- **Testing**: pytest with pytest-django
- **Deployment**: Render

## Documentation

- [Setup Instructions](docs/SETUP_INSTRUCTIONS.md) - Detailed setup, database configuration, and deployment
- [Import Instructions](docs/IMPORT_INSTRUCTIONS.md) - Data import procedures
- [Testing Guide](docs/TESTING_GUIDE.md) - Manual testing procedures