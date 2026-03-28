from django.core.management.base import BaseCommand

from members.models import Member


class Command(BaseCommand):
    help = "Strip trailing .0 from home_zip values (pandas import artifact)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, runs as dry run.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        members = Member.objects.filter(home_zip__endswith=".0")
        count = members.count()

        if count == 0:
            self.stdout.write("No zip codes with .0 found. Nothing to do.")
            return

        if not apply:
            self.stdout.write(f"DRY RUN — no changes made")
            self.stdout.write(f"Found {count} members with .0 in zip code:\n")

        updated = 0
        for member in members:
            old_zip = member.home_zip
            new_zip = old_zip[:-2]  # strip ".0"
            if apply:
                member.home_zip = new_zip
                member.save(update_fields=["home_zip"])
                updated += 1
            else:
                self.stdout.write(f"  {member}: {old_zip} -> {new_zip}")

        if apply:
            self.stdout.write(f"Updated {updated} zip codes.")
        else:
            self.stdout.write(f"\nRun with --apply to fix these {count} records.")
