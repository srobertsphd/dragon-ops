from django.core.management.base import BaseCommand
from members.models import Member


class Command(BaseCommand):
    help = "Backfill new_expiration_date on the most recent payment for each active non-Life member."

    def handle(self, *args, **options):
        members = (
            Member.objects.filter(status="active")
            .exclude(member_type__member_type="Life")
            .prefetch_related("payments")
        )

        updated = 0
        for member in members:
            payment = member.payments.order_by("-date", "-created_at").first()
            if payment and not payment.new_expiration_date:
                payment.new_expiration_date = member.expiration_date
                payment.save(update_fields=["new_expiration_date"])
                updated += 1

        self.stdout.write(f"Backfilled {updated} payments.")
