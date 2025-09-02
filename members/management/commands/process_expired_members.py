from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from members.models import Member


class Command(BaseCommand):
    help = "Process member lifecycle - inactivate expired members and reinstate members"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--grace-period-days",
            type=int,
            default=90,  # 3 months
            help="Days past expiration before auto-inactivation (default: 90)",
        )
        parser.add_argument(
            "--reinstate-member",
            type=str,
            help="Reinstate specific member by UUID",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        reinstate_uuid = options.get("reinstate_member")

        if reinstate_uuid:
            self.reinstate_member(reinstate_uuid, dry_run)
        else:
            self.process_expired_members(options)

    def reinstate_member(self, member_uuid, dry_run):
        """Reinstate a specific member by UUID"""
        try:
            member = Member.objects.get(member_uuid=member_uuid, status="inactive")
        except Member.DoesNotExist:
            self.stdout.write("❌ Member not found or not inactive")
            return

        self.stdout.write(f"\n🔄 Reinstating: {member.first_name} {member.last_name}")

        # Try to get their preferred ID back
        preferred_available = not Member.objects.filter(
            status="active", member_id=member.preferred_member_id
        ).exists()

        if preferred_available:
            target_id = member.preferred_member_id
            msg = f"✅ Restored preferred ID #{target_id}"
        else:
            target_id = Member.get_next_available_member_id()
            if target_id:
                msg = f"⚠️ New ID #{target_id} (preferred #{member.preferred_member_id} taken)"
            else:
                self.stdout.write("❌ No member IDs available (1-1000 range full)")
                return

        if not dry_run:
            member.member_id = target_id
            member.status = "active"
            member.date_inactivated = None
            member.save()
            self.stdout.write(f"   {msg}")
        else:
            self.stdout.write(f"   🔍 Would reinstate: {msg}")

    def process_expired_members(self, options):
        """Process expired members for inactivation"""
        dry_run = options["dry_run"]
        grace_period_days = options["grace_period_days"]

        # Calculate cutoff date
        cutoff_date = timezone.now().date() - timedelta(days=grace_period_days)

        self.stdout.write(f"\n🔍 Processing members expired before: {cutoff_date}")
        if dry_run:
            self.stdout.write("   🔍 DRY RUN - No changes will be made")

        # Find expired members
        expired_members = Member.objects.filter(
            status="active", expiration_date__lt=cutoff_date
        ).order_by("expiration_date")

        if not expired_members.exists():
            self.stdout.write("   ✅ No members found requiring inactivation")
            self.show_available_ids()
            return

        self.stdout.write(
            f"\n📋 Found {expired_members.count()} members to inactivate:"
        )

        recycled_ids = []
        for member in expired_members:
            if not dry_run:
                if member.member_id:
                    recycled_ids.append(member.member_id)
                member.status = "inactive"
                member.member_id = None
                member.date_inactivated = timezone.now().date()
                member.save()
                self.stdout.write(
                    f"   ✅ {member.first_name} {member.last_name} (ID #{recycled_ids[-1]} recycled)"
                )
            else:
                if member.member_id:
                    recycled_ids.append(member.member_id)
                self.stdout.write(
                    f"   🔍 Would inactivate: {member.first_name} {member.last_name} (ID #{member.member_id})"
                )

        # Summary
        if dry_run:
            self.stdout.write(
                f"\n🔍 Would inactivate {len(expired_members)} members, recycle IDs: {recycled_ids}"
            )
        else:
            self.stdout.write(
                f"\n✅ Inactivated {len(expired_members)} members, recycled IDs: {recycled_ids}"
            )

        self.show_available_ids()

    def show_available_ids(self):
        """Show current status of ID pool (1-1000)"""
        # Get all active member IDs
        active_ids = set(
            Member.objects.filter(status="active", member_id__isnull=False).values_list(
                "member_id", flat=True
            )
        )

        # Total possible IDs (1-1000)
        all_possible_ids = set(range(1, 1001))
        available_ids = all_possible_ids - active_ids

        self.stdout.write("\n🎯 ID Pool Status:")
        self.stdout.write(f"   Active members: {len(active_ids)}")
        self.stdout.write(f"   Available IDs: {len(available_ids)}")
        self.stdout.write(
            f"   Next available: {min(available_ids) if available_ids else 'None'}"
        )

        if len(available_ids) < 50:
            self.stdout.write(
                f"   ⚠️  Warning: Only {len(available_ids)} IDs available!"
            )
