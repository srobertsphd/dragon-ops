# Alano Club Member Management System

A Django-based web application for managing club members, payments, and organizational data.

## Project Structure

```
alano-club/
├── alano_club_site/          # Django project settings
├── members/                  # Main Django app
│   └── management/
│       └── commands/         # Django management commands for data import
├── data/                     # Data files
│   └── 2025_09_02/
│       ├── original/         # Original Excel files
│       └── cleaned/          # Cleaned CSV files ready for import
├── scripts/                  # ETL scripts for data processing
│   ├── clean_member_data.py
│   ├── clean_dead_data.py
│   ├── clean_member_payments.py
│   └── DATA_PREP_DESCRIPTION.md
├── docs/                     # Project documentation
│   ├── SETUP_INSTRUCTIONS.md
│   ├── IMPORT_INSTRUCTIONS.md
│   └── ...
├── tests/                    # Test files
├── logs/                     # Import logs and reports
├── manage.py                 # Django management script
├── pyproject.toml            # Python project configuration
├── pytest.ini               # Pytest configuration
└── README.md                 # This file
```

## Features

- **Member Management**: Add, edit, view members with detailed contact information
- **Payment Tracking**: Record and track membership dues and payments
- **Member Types**: Configure different membership categories
- **Admin Interface**: Full administrative control via Django Admin
- **Data Import**: Tools for importing existing Excel data
- **Modern UI**: Bootstrap-styled forms and interfaces

## Quick Start

1. **Install UV** (if not already installed):
   
   **macOS and Linux:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   
   After installation, restart your terminal or run:
   ```bash
   source $HOME/.cargo/env
   ```
   
   For alternative installation methods, see the [UV installation guide](https://docs.astral.sh/uv/getting-started/installation/).

2. **Create virtual environment:**
   ```bash
   uv venv
   ```

3. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   uv sync
   ```

5. **Run development server:**
   ```bash
   python manage.py runserver 8001
   ```

6. **Access admin interface:**
   - URL: http://127.0.0.1:8001/admin/
   - Login with your admin credentials (currently: alanoclub/alanoclub)

## Data Management

**Data Cleaning and Transformation:**

The ETL scripts for cleaning and transforming data are located in the `scripts/` directory. See [`scripts/DATA_PREP_DESCRIPTION.md`](scripts/DATA_PREP_DESCRIPTION.md) for detailed information about the transformation scripts and data processing steps.

**Note:** The scripts are currently configured to process `Excel` data from `data/2025_09_02/original/` (September 2, 2025). The cleaned output files are saved to `data/2025_09_02/cleaned/` in `.csv` format.

**Run the transformation scripts:**
```bash
# From the project root directory
python scripts/clean_member_data.py
python scripts/clean_dead_data.py
python scripts/clean_member_payments.py
```

**Current data:**
- 325 active members
- 1,337 payment records  
- 10 member types
- 11 payment methods

## Next Steps

See [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md) for detailed setup, database configuration, and deployment instructions.
