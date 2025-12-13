import uuid
from django.db import models
from django.utils import timezone


STATE_CHOICES = [
    ("CA", "California (CA)"),
    ("AL", "Alabama (AL)"),
    ("AK", "Alaska (AK)"),
    ("AZ", "Arizona (AZ)"),
    ("AR", "Arkansas (AR)"),
    ("CO", "Colorado (CO)"),
    ("CT", "Connecticut (CT)"),
    ("DE", "Delaware (DE)"),
    ("FL", "Florida (FL)"),
    ("GA", "Georgia (GA)"),
    ("HI", "Hawaii (HI)"),
    ("ID", "Idaho (ID)"),
    ("IL", "Illinois (IL)"),
    ("IN", "Indiana (IN)"),
    ("IA", "Iowa (IA)"),
    ("KS", "Kansas (KS)"),
    ("KY", "Kentucky (KY)"),
    ("LA", "Louisiana (LA)"),
    ("ME", "Maine (ME)"),
    ("MD", "Maryland (MD)"),
    ("MA", "Massachusetts (MA)"),
    ("MI", "Michigan (MI)"),
    ("MN", "Minnesota (MN)"),
    ("MS", "Mississippi (MS)"),
    ("MO", "Missouri (MO)"),
    ("MT", "Montana (MT)"),
    ("NE", "Nebraska (NE)"),
    ("NV", "Nevada (NV)"),
    ("NH", "New Hampshire (NH)"),
    ("NJ", "New Jersey (NJ)"),
    ("NM", "New Mexico (NM)"),
    ("NY", "New York (NY)"),
    ("NC", "North Carolina (NC)"),
    ("ND", "North Dakota (ND)"),
    ("OH", "Ohio (OH)"),
    ("OK", "Oklahoma (OK)"),
    ("OR", "Oregon (OR)"),
    ("PA", "Pennsylvania (PA)"),
    ("RI", "Rhode Island (RI)"),
    ("SC", "South Carolina (SC)"),
    ("SD", "South Dakota (SD)"),
    ("TN", "Tennessee (TN)"),
    ("TX", "Texas (TX)"),
    ("UT", "Utah (UT)"),
    ("VT", "Vermont (VT)"),
    ("VA", "Virginia (VA)"),
    ("WA", "Washington (WA)"),
    ("WV", "West Virginia (WV)"),
    ("WI", "Wisconsin (WI)"),
    ("WY", "Wyoming (WY)"),
]


class MemberType(models.Model):
    """Simple membership types lookup table"""

    member_type = models.CharField(max_length=50, unique=True)  # From CSV: member_type
    member_dues = models.DecimalField(
        max_digits=8, decimal_places=2
    )  # From CSV: member_dues
    num_months = models.IntegerField()  # From CSV: num_months

    class Meta:
        ordering = ["member_type"]
        db_table = "members_membertype"

    def __str__(self):
        return self.member_type


class PaymentMethod(models.Model):
    """Simple payment methods lookup table"""

    payment_method = models.CharField(
        max_length=50, unique=True
    )  # From CSV: payment_method

    class Meta:
        ordering = ["payment_method"]
        db_table = "members_paymentmethod"

    def __str__(self):
        return self.payment_method


class MemberManager(models.Manager):
    """Custom manager for Member ID management and member operations"""

    def get_next_available_id(self):
        """Get the next available member ID (1-1000)"""
        # Get all active member IDs
        active_ids = set(
            self.filter(status="active", member_id__isnull=False).values_list(
                "member_id", flat=True
            )
        )

        # Find first available ID in range 1-1000
        for id_num in range(1, 1001):
            if id_num not in active_ids:
                return id_num

        return None  # No IDs available

    def is_member_id_available(self, member_id):
        """Check if a specific member_id is available for assignment"""
        return not self.filter(member_id=member_id, status="active").exists()

    def get_active_member_ids(self):
        """Get sorted list of all currently active member IDs"""
        return list(
            self.filter(member_id__isnull=False, status="active")
            .values_list("member_id", flat=True)
            .order_by("member_id")
        )

    def get_available_member_ids(self):
        """Get sorted list of all available member IDs (1-1000)"""
        active_ids = set(self.get_active_member_ids())
        return [i for i in range(1, 1001) if i not in active_ids]

    def get_expired_for_deactivation(self):
        """Get members who are expired 3+ months and should be deactivated"""
        from datetime import date, timedelta

        three_months_ago = date.today() - timedelta(days=90)
        return self.filter(status="active", expiration_date__lt=three_months_ago)

    def get_expired_without_payment(self, days_threshold=90):
        """
        Get active members expired N+ days with no payment after expiration.

        Args:
            days_threshold: Number of days past expiration (default: 90)

        Returns:
            QuerySet of eligible members
        """
        from datetime import date, timedelta
        from django.db.models import Max

        cutoff_date = date.today() - timedelta(days=days_threshold)

        # Get active members expired beyond threshold
        expired_members = self.filter(status="active", expiration_date__lt=cutoff_date)

        # Annotate with last payment date after expiration
        expired_members = expired_members.annotate(
            last_payment_after_expiration=Max(
                "payments__date",
                filter=models.Q(payments__date__gt=models.F("expiration_date")),
            )
        )

        # Filter to only those with no payment after expiration
        return expired_members.filter(last_payment_after_expiration__isnull=True)

    def get_member_for_reactivation(self, first_name, last_name):
        """Find inactive member by name for reactivation"""
        return self.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            status="inactive",
        ).first()

    def create_new_member(self, **kwargs):
        """Create new member with auto-assigned or custom member_id"""
        # Extract member_id if provided
        custom_member_id = kwargs.pop("member_id", None)

        member = self.create(**kwargs)
        if member.status == "active":
            if custom_member_id is not None:
                # Use provided member_id
                member.member_id = custom_member_id
            else:
                # Auto-assign next available ID
                member.member_id = self.get_next_available_id()
            member.preferred_member_id = member.member_id
            member.save()
        return member


class Member(models.Model):
    """Main member information with dual key system"""

    # Custom manager for ID management
    objects = MemberManager()

    # Dual Key System (Setup Instructions)
    member_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)  # PERMANENT ID
    member_id = models.IntegerField(
        null=True, blank=True, unique=True
    )  # RECYCLABLE (1-1000)
    preferred_member_id = models.IntegerField(
        null=True, blank=True
    )  # For reinstatement

    # Basic Information (CSV: members.csv)
    first_name = models.CharField(max_length=50)  # "First Name"
    last_name = models.CharField(max_length=50)  # "Last Name"
    email = models.EmailField(blank=True)  # "E Mail"

    # Membership Information
    member_type = models.ForeignKey(MemberType, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("deceased", "Deceased"),
        ],
        default="active",
    )
    expiration_date = models.DateField()  # Current membership expires

    # Important Dates (CSV: members.csv)
    milestone_date = models.DateField(
        null=True, blank=True
    )  # "Milestone" - Sobriety date
    date_joined = models.DateField()  # "Date Joined" - Club membership start
    date_inactivated = models.DateField(null=True, blank=True)

    # Contact Information (CSV: current_members.csv)
    home_address = models.TextField(blank=True)  # "home_address"
    home_city = models.CharField(max_length=100, blank=True)  # "home_city"
    home_state = models.CharField(
        max_length=2, blank=True, choices=STATE_CHOICES
    )  # "home_state"
    home_zip = models.CharField(max_length=10, blank=True)  # "home_zip"
    home_phone = models.CharField(max_length=20, blank=True)  # "home_phone"

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        db_table = "members_member"
        indexes = [
            models.Index(fields=["member_id"]),
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expiration_date"]),
        ]

    def __str__(self):
        display_id = self.member_id if self.member_id else "No ID"
        return f"#{display_id} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def days_expired(self):
        """Calculate days since expiration date"""
        from datetime import date

        if self.expiration_date:
            return (date.today() - self.expiration_date).days
        return 0

    @property
    def last_payment_date(self):
        """Get the most recent payment date, or None"""
        last_payment = self.payments.order_by("-date").first()
        return last_payment.date if last_payment else None

    def is_membership_expired(self):
        """Check if membership has expired"""
        return self.expiration_date < timezone.now().date()

    def is_expired_for_deactivation(self):
        """Check if member is expired 3+ months and should be deactivated"""
        from datetime import date, timedelta

        if self.expiration_date:
            three_months_ago = date.today() - timedelta(days=90)
            return self.expiration_date < three_months_ago
        return False

    def deactivate(self):
        """Move member to inactive status and release member_id for recycling"""
        if self.member_id:
            self.preferred_member_id = self.member_id  # Save for reactivation
            self.member_id = None  # Release ID back to pool
        self.status = "inactive"
        self.date_inactivated = timezone.now().date()
        self.save()

    def reactivate(self):
        """Reactivate member, trying to restore preferred_member_id"""
        # Try to get preferred ID first
        if self.preferred_member_id and Member.objects.is_member_id_available(
            self.preferred_member_id
        ):
            self.member_id = self.preferred_member_id
        else:
            # Get next available ID
            self.member_id = Member.objects.get_next_available_id()

        self.status = "active"
        self.date_inactivated = None
        self.save()


class Payment(models.Model):
    """Payment records linked to members via UUID"""

    # Relationships (CRITICAL: UUID not member_id!)
    member = models.ForeignKey(
        Member, on_delete=models.PROTECT, related_name="payments"
    )
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)

    # Payment Details (CSV: payments.csv)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # "Amount"
    date = models.DateField()  # "Date"
    receipt_number = models.CharField(max_length=50, blank=True)  # "Reciept No."

    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        db_table = "members_payment"
        indexes = [
            models.Index(fields=["member", "date"]),
            models.Index(fields=["date"]),
            models.Index(fields=["amount"]),
        ]

    def __str__(self):
        return f"{self.member.full_name} - ${self.amount} on {self.date}"
