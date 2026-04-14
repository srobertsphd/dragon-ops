"""
Restore dev database from the most recent prod backup.

Usage:
    python manage.py restore_dev_from_backup
    python manage.py restore_dev_from_backup --file backups/prod/backup_prod_2026-04-04.json
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Restore dev database from most recent prod backup"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            help="Path to specific backup file (default: most recent in backups/prod/)",
        )
        parser.add_argument(
            "--skip-confirm",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        # Safety: refuse to run against production
        current_host = settings.DATABASES["default"].get("HOST", "")
        prod_url = os.getenv("DATABASE_URL_PROD", "")
        if prod_url and current_host in prod_url:
            self.stdout.write(self.style.ERROR(
                "SAFETY CHECK FAILED: DATABASE_URL points to production. Aborting."
            ))
            return

        # Find backup file
        if options["file"]:
            backup_path = Path(options["file"])
        else:
            backup_dir = Path("backups/prod")
            if not backup_dir.exists():
                self.stdout.write(self.style.ERROR("No backups/prod/ directory found."))
                return
            backups = sorted(backup_dir.glob("*.json"))
            if not backups:
                self.stdout.write(self.style.ERROR("No backup files found in backups/prod/"))
                return
            backup_path = backups[-1]

        if not backup_path.exists():
            self.stdout.write(self.style.ERROR(f"File not found: {backup_path}"))
            return

        size = backup_path.stat().st_size
        self.stdout.write(f"Backup file: {backup_path} ({size:,} bytes)")
        self.stdout.write(f"Target database: {current_host}")

        if not options["skip_confirm"]:
            confirm = input("This will REPLACE all dev data. Continue? (yes/no): ")
            if confirm.lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        # Flush dev database
        self.stdout.write("Flushing dev database...")
        call_command("flush", "--noinput", verbosity=0)
        self.stdout.write(self.style.SUCCESS("  Done."))

        # Load backup directly (no subprocess)
        self.stdout.write("Loading backup data (this may take a few minutes)...")
        call_command("loaddata", str(backup_path), verbosity=1)
        self.stdout.write(self.style.SUCCESS("  Done."))

        # Reset sequences
        self.stdout.write("Resetting sequences...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT setval(
                    'members_payment_id_seq',
                    COALESCE((SELECT MAX(id) FROM members_payment), 1),
                    true
                )
            """)
        self.stdout.write(self.style.SUCCESS("  Done."))

        self.stdout.write(self.style.SUCCESS("\nRestore completed successfully."))
