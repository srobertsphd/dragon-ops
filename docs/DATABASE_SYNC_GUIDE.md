# Database Sync Guide: Production to Development

**Created:** December 2025  
**Purpose:** Guide for syncing production data to development database and setting up periodic updates.

---

## Overview

This guide explains how to copy data from your production Supabase database to your development database, and how to set up periodic syncing.

---

## Methods Comparison

### Method 1: Django Management Command (Recommended) ⭐

**Best for:** Regular syncing, ease of use, safety checks

**Pros:**
- ✅ Built-in safety checks (won't run on production)
- ✅ Handles sequences automatically
- ✅ Easy to run: `python manage.py sync_prod_to_dev`
- ✅ Can be automated
- ✅ Uses Django's native dumpdata/loaddata

**Cons:**
- ⚠️ Requires both databases to be accessible
- ⚠️ Slower for very large datasets

**When to use:** Regular development workflow, weekly/monthly syncs

---

### Method 2: pg_dump / psql (PostgreSQL Tools)

**Best for:** One-time full database copy, fastest method

**Pros:**
- ✅ Fastest method
- ✅ Complete copy (schema + data + sequences)
- ✅ Handles all PostgreSQL features

**Cons:**
- ⚠️ Requires PostgreSQL client tools installed
- ⚠️ More complex commands
- ⚠️ No built-in safety checks

**When to use:** Initial setup, major migrations, when you need exact copy

**Requirements:**
- PostgreSQL client tools (`pg_dump`, `psql`)
- Access to both database URLs

---

### Method 3: Supabase Dashboard Export/Import

**Best for:** Manual one-time exports, small datasets

**Pros:**
- ✅ No command line needed
- ✅ GUI-based

**Cons:**
- ⚠️ Manual process
- ⚠️ May have size limits
- ⚠️ Doesn't preserve all metadata
- ⚠️ Time-consuming for regular use

**When to use:** One-time exports, troubleshooting

---

## Recommended Approach

**For regular syncing:** Use Django Management Command (Method 1)  
**For initial setup:** Use pg_dump/psql (Method 2) if you have the tools, otherwise use Method 1

---

## Setup: Using Django Management Command

### Prerequisites

1. **Ensure `.env` file has both URLs:**
   ```bash
   DATABASE_URL_PROD=postgresql://postgres.xxxxx:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   DATABASE_URL_DEV=postgresql://postgres.yyyyy:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:6543/postgres
   DATABASE_URL=${DATABASE_URL_DEV}
   ```

2. **Verify you're connected to dev database:**
   ```bash
   python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['HOST'])"
   ```
   Should show your dev database hostname.

### Usage

**Basic sync:**
```bash
python manage.py sync_prod_to_dev
```

**Dry run (see what would happen):**
```bash
python manage.py sync_prod_to_dev --dry-run
```

**Skip confirmation (for automation):**
```bash
python manage.py sync_prod_to_dev --skip-confirm
```

### What It Does

1. ✅ **Safety Check:** Verifies you're connected to dev database (not production)
2. ✅ **Export:** Exports data from production database
3. ✅ **Clear:** Clears development database (keeps schema)
4. ✅ **Import:** Imports production data into development
5. ✅ **Reset Sequences:** Resets auto-increment sequences

### Safety Features

- Won't run if connected to production database
- Requires confirmation prompt (unless `--skip-confirm`)
- Only affects development database
- Production database is read-only during sync

---

## Setup: Using pg_dump / psql (Alternative)

### Prerequisites

Install PostgreSQL client tools:

**Ubuntu/WSL2:**
```bash
sudo apt-get update
sudo apt-get install postgresql-client
```

**macOS:**
```bash
brew install postgresql
```

**Windows:**
Download from: https://www.postgresql.org/download/windows/

### Usage

**Step 1: Export from production**
```bash
pg_dump "postgresql://postgres.xxxxx:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" \
  --no-owner \
  --no-acl \
  --clean \
  --if-exists \
  > production_backup.sql
```

**Step 2: Import into development**
```bash
psql "postgresql://postgres.yyyyy:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:6543/postgres" \
  < production_backup.sql
```

**Step 3: Clean up**
```bash
rm production_backup.sql
```

### Notes

- Replace `[PASSWORD]` with actual passwords
- Replace `xxxxx` and `yyyyy` with your project identifiers
- `--no-owner` and `--no-acl` prevent permission issues
- `--clean` drops tables before recreating
- `--if-exists` prevents errors if tables don't exist

---

## Periodic Updates: Recommended Workflow

### Option 1: Manual Sync (Recommended for now)

**When to sync:**
- Weekly or monthly
- Before starting major development work
- After production has significant data changes

**Process:**
1. Ensure `.env` points to dev database (`DATABASE_URL=${DATABASE_URL_DEV}`)
2. Run: `python manage.py sync_prod_to_dev`
3. Confirm when prompted
4. Wait for sync to complete

**Time estimate:** 2-5 minutes depending on data size

---

### Option 2: Automated Script (Future)

Create a simple script you can run:

**`scripts/sync_dev.sh`:**
```bash
#!/bin/bash
# Sync production to development database

echo "🔄 Syncing production data to development..."

# Ensure we're using dev database
export DATABASE_URL=$(grep DATABASE_URL_DEV .env | cut -d '=' -f2-)

# Run sync command
python manage.py sync_prod_to_dev --skip-confirm

echo "✅ Sync complete!"
```

**Make it executable:**
```bash
chmod +x scripts/sync_dev.sh
```

**Run it:**
```bash
./scripts/sync_dev.sh
```

---

### Option 3: Scheduled Task (Advanced)

For fully automated syncing, you could set up a cron job or scheduled task, but this is **not recommended** for development databases as you may lose work-in-progress data.

---

## Troubleshooting

### Issue: "DATABASE_URL_PROD not found"

**Solution:** Add `DATABASE_URL_PROD` to your `.env` file with production Session Pooler URL.

### Issue: "SAFETY CHECK FAILED: Connected to PRODUCTION"

**Solution:** Your `DATABASE_URL` in `.env` is pointing to production. Change it to `${DATABASE_URL_DEV}`.

### Issue: Export/Import fails

**Check:**
1. Both database URLs are correct
2. Passwords are correct
3. Both databases are accessible
4. You have network connectivity

### Issue: Sequences not reset

**Solution:** The command tries to reset sequences automatically. If issues persist, you can manually reset:

```sql
-- In Supabase SQL Editor for dev database
SELECT setval('members_member_member_id_seq', (SELECT MAX(member_id) FROM members_member));
```

---

## Best Practices

1. **Always verify you're on dev database** before syncing
2. **Sync regularly** (weekly/monthly) to keep dev data current
3. **Don't sync during active development** - you'll lose local changes
4. **Backup important dev work** before syncing if needed
5. **Use dry-run first** if unsure: `--dry-run` flag

---

## Quick Reference

**Sync production to dev:**
```bash
python manage.py sync_prod_to_dev
```

**Check which database you're connected to:**
```bash
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['HOST'])"
```

**Verify migrations are applied:**
```bash
python manage.py showmigrations
```

---

## Related Documentation

- [Supabase Connection Setup](./SUPABASE_CONNECTION_SETUP.md)
- [Change Log](./CHANGE_LOG.md)

