import uuid
from django.db import models
from django.utils import timezone


class MemberType(models.Model):
    """Different types of membership with dues and coverage periods"""

    member_type_id = models.IntegerField(primary_key=True)  # From CSV: MemberTypeID
    name = models.CharField(max_length=50, unique=True)  # From CSV: MemberType
    monthly_dues = models.DecimalField(
        max_digits=8, decimal_places=2
    )  # From CSV: Member Dues
    coverage_months = models.DecimalField(
        max_digits=5, decimal_places=1
    )  # From CSV: NumMonths
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        db_table = "members_membertype"

    def __str__(self):
        return f"{self.name} (${self.monthly_dues}/month)"


class PaymentMethod(models.Model):
    """Payment methods with credit card designation"""

    payment_method_id = models.IntegerField(
        primary_key=True
    )  # From CSV: PaymentMethodID
    name = models.CharField(max_length=50, unique=True)  # From CSV: PaymentMethod
    is_credit_card = models.BooleanField(default=False)  # From CSV: Credit Card?
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        db_table = "members_paymentmethod"

    def __str__(self):
        return self.name


class Member(models.Model):
    """Main member information with dual key system"""

    # Dual Key System (Setup Instructions)
    member_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)  # PERMANENT ID
    member_id = models.IntegerField(
        null=True, blank=True, unique=True
    )  # RECYCLABLE (1-1000)
    preferred_member_id = models.IntegerField()  # For reinstatement

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

    # Contact Information (CSV: members.csv)
    home_address = models.TextField(blank=True)  # "Home Address"
    home_country = models.CharField(
        max_length=50, blank=True, default="US"
    )  # "Home Country"
    home_phone = models.CharField(max_length=20, blank=True)  # "Home Phone"

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

    def is_membership_expired(self):
        """Check if membership has expired"""
        return self.expiration_date < timezone.now().date()


class Payment(models.Model):
    """Payment records linked to members via UUID"""

    payment_id = models.IntegerField(primary_key=True)  # From CSV: Payment ID

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
