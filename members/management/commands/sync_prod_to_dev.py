"""
Django management command to sync production data to development database.

Usage:
    python manage.py sync_prod_to_dev

This command:
1. Exports data from production database
2. Clears development database
3. Imports data into development database
4. Resets sequences

Safety:
- Only works when DATABASE_URL points to dev database
- Requires DATABASE_URL_PROD to be set in .env
- Will not run if connected to production database
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
import sys
from dotenv import load_dotenv


class Command(BaseCommand):
    help = "Sync production data to development database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without actually doing it",
        )
        parser.add_argument(
            "--skip-confirm",
            action="store_true",
            help="Skip confirmation prompt (use with caution)",
        )

    def handle(self, *args, **options):
        load_dotenv()

        # Safety check: Verify we're connected to dev database
        current_db = settings.DATABASES["default"]
        current_host = current_db.get("HOST", "")

        # Check if we're connected to production (safety check)
        prod_url = os.getenv("DATABASE_URL_PROD", "")
        if prod_url and current_host in prod_url:
            self.stdout.write(
                self.style.ERROR(
                    "❌ SAFETY CHECK FAILED: You appear to be connected to PRODUCTION database!"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Please set DATABASE_URL to point to DEV database in .env file"
                )
            )
            return

        # Check if DATABASE_URL_PROD is set
        if not prod_url:
            self.stdout.write(
                self.style.ERROR("❌ DATABASE_URL_PROD not found in .env file")
            )
            self.stdout.write("Please add DATABASE_URL_PROD to your .env file")
            return

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
            self.stdout.write(f"Current database: {current_host}")
            self.stdout.write(f"Production URL exists: {bool(prod_url)}")
            return

        # Confirmation prompt
        if not options["skip_confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  This will REPLACE all data in your development database with production data."
                )
            )
            self.stdout.write(f"Current database host: {current_host}")
            confirm = input("Are you sure you want to continue? (yes/no): ")
            if confirm.lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        self.stdout.write(self.style.SUCCESS("Starting data sync..."))

        # Step 1: Export from production
        self.stdout.write("Step 1: Exporting data from production...")
        try:
            # Temporarily switch to production database
            # We'll use dumpdata with a custom database setting
            import tempfile
            import subprocess

            dump_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            )
            dump_file.close()

            # Export from production using DATABASE_URL_PROD
            self.stdout.write("  Exporting production data...")
            # Use subprocess to run dumpdata with production URL
            # Use sys.executable to ensure we use the same Python interpreter
            result = subprocess.run(
                [
                    sys.executable,
                    "manage.py",
                    "dumpdata",
                    "--natural-foreign",
                    "--natural-primary",
                    "--exclude=auth.Permission",
                    "--exclude=admin.LogEntry",
                    "--exclude=sessions.Session",
                ],
                env={**os.environ, "DATABASE_URL": prod_url},
                capture_output=True,
                text=True,
                cwd=os.getcwd(),  # Ensure we're in the right directory
            )

            if result.returncode != 0:
                self.stdout.write(self.style.ERROR(f"Export failed: {result.stderr}"))
                if result.stdout:
                    self.stdout.write(f"  stdout: {result.stdout[:500]}")
                return

            # Check if we got data
            if not result.stdout or len(result.stdout.strip()) < 100:
                self.stdout.write(
                    self.style.WARNING("  ⚠️  Export seems empty or very small")
                )
                self.stdout.write(f"  Output length: {len(result.stdout)}")

            # Write to file
            with open(dump_file.name, "w") as f:
                f.write(result.stdout)

            file_size = os.path.getsize(dump_file.name)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Exported to {dump_file.name} ({file_size:,} bytes)"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Export failed: {e}"))
            return

        # Step 2: Clear development database (except migrations table)
        self.stdout.write("Step 2: Clearing development database...")
        try:
            # Flush database (clears all data but keeps structure)
            call_command("flush", "--noinput", verbosity=0)
            self.stdout.write(self.style.SUCCESS("  ✓ Development database cleared"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Clear failed: {e}"))
            return

        # Step 3: Import into development database
        self.stdout.write("Step 3: Importing data into development database...")
        self.stdout.write("  This may take a few minutes for large datasets...")
        self.stdout.write(f"  Loading from: {dump_file.name}")
        try:
            # Use subprocess for loaddata to have better control and see real-time output
            import subprocess

            self.stdout.write("  Starting import process...")

            process = subprocess.Popen(
                [
                    sys.executable,
                    "manage.py",
                    "loaddata",
                    dump_file.name,
                    "--verbosity=2",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env={
                    **os.environ,
                    "DJANGO_SETTINGS_MODULE": "alano_club_site.settings",
                },
            )

            # Stream output in real-time
            for line in process.stdout:
                self.stdout.write(f"  {line.rstrip()}")

            process.wait()

            if process.returncode != 0:
                raise Exception(f"loaddata exited with code {process.returncode}")

            self.stdout.write(
                self.style.SUCCESS("  ✓ Data imported into development database")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Import failed: {e}"))
            self.stdout.write(f"  Error details: {str(e)}")
            # Check if file exists and show size
            try:
                if os.path.exists(dump_file.name):
                    size = os.path.getsize(dump_file.name)
                    self.stdout.write(f"  Dump file size: {size:,} bytes")
            except Exception:
                pass
            return

        # Step 4: Reset sequences
        # Note: member_id is NOT an auto-increment field, so it has no sequence
        # Only reset sequences that actually exist (like payment.id)
        self.stdout.write("Step 4: Resetting sequences...")
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                # Reset payment sequence (the only critical one)
                cursor.execute(
                    """
                    SELECT setval(
                        'members_payment_id_seq',
                        COALESCE((SELECT MAX(id) FROM members_payment), 1),
                        true
                    )
                    """
                )
                self.stdout.write("  ✓ Reset members_payment_id_seq")

            self.stdout.write(self.style.SUCCESS("  ✓ Sequences reset"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Sequence reset had issues: {e}"))

        # Cleanup
        try:
            os.unlink(dump_file.name)
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS("\n✅ Data sync completed successfully!"))
        self.stdout.write("Your development database now contains production data.")
