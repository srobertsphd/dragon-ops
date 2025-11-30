"""
Business logic services for members and payments.

This module contains service classes that encapsulate business logic
for member and payment operations, separating concerns from views.
"""

from decimal import Decimal
from datetime import datetime, date
from .models import Member, MemberType, Payment, PaymentMethod
from .utils import add_months_to_date, ensure_end_of_month


class PaymentService:
    """Service class for payment-related business logic"""

    @staticmethod
    def calculate_expiration(member, payment_amount, override_expiration=None):
        """
        Calculate new expiration date based on payment amount.

        Args:
            member: Member instance
            payment_amount: Decimal payment amount
            override_expiration: Optional date to override calculation

        Returns:
            date: New expiration date
        """
        if override_expiration:
            return override_expiration

        if member.member_type and member.member_type.member_dues > 0:
            months_paid = float(payment_amount) / float(member.member_type.member_dues)
            total_months_to_add = int(months_paid)
            return add_months_to_date(member.expiration_date, total_months_to_add)
        else:
            return add_months_to_date(member.expiration_date, 1)

    @staticmethod
    def calculate_suggested_payment_for_new_member(member_type, start_date=None):
        """
        Calculate suggested payment amount for new member to get to end of next month.

        This calculates the payment needed to cover:
        - Remainder of current month (partial)
        - Plus full next month
        - To reach the end of the next month

        Args:
            member_type: MemberType instance
            start_date: Starting date (defaults to today)

        Returns:
            Decimal: Suggested payment amount
        """
        if start_date is None:
            start_date = date.today()

        if member_type and member_type.member_dues > 0:
            # Calculate payment for 1 month (to get to end of next month)
            # This covers remainder of current month + full next month
            return Decimal(str(member_type.member_dues))
        else:
            # Default to 1 month payment if no dues specified
            return Decimal("0.00")

    @staticmethod
    def calculate_expiration_for_new_member(
        member_type, payment_amount, start_date=None, override_expiration=None
    ):
        """
        Calculate expiration date for a new member based on payment amount.

        Rules:
        - Always rounds up to at least the end of the current month (never less)
        - Calculates months paid based on payment_amount / monthly_dues
        - Result is always the last day of a month (current or future)
        - Supports override_expiration parameter

        Args:
            member_type: MemberType instance
            payment_amount: Decimal payment amount
            start_date: Starting date for calculation (defaults to today)
            override_expiration: Optional date to override calculation

        Returns:
            date: New expiration date (always end of month)
        """
        if override_expiration:
            return ensure_end_of_month(override_expiration)

        if start_date is None:
            start_date = date.today()

        # Ensure start_date is end of current month
        current_month_end = ensure_end_of_month(start_date)

        if member_type and member_type.member_dues > 0:
            months_paid = float(payment_amount) / float(member_type.member_dues)
            total_months_to_add = int(months_paid)

            # If payment is less than 1 month, still give them until end of current month
            if total_months_to_add == 0:
                return current_month_end

            # Calculate expiration from end of current month
            return add_months_to_date(current_month_end, total_months_to_add)
        else:
            # Default to end of current month if no dues specified
            return current_month_end

    @staticmethod
    def process_payment(member, payment_data):
        """
        Create payment record and update member expiration.

        Args:
            member: Member instance
            payment_data: Dict with payment details:
                - payment_method_id: PaymentMethod ID
                - amount: Payment amount (string)
                - payment_date: Payment date (ISO format string)
                - receipt_number: Receipt number (string)
                - new_expiration: New expiration date (ISO format string)

        Returns:
            tuple: (payment_instance, was_reactivated_bool)
        """
        payment_method = PaymentMethod.objects.get(pk=payment_data["payment_method_id"])

        # Create payment
        payment = Payment.objects.create(
            member=member,
            payment_method=payment_method,
            amount=Decimal(payment_data["amount"]),
            date=datetime.fromisoformat(payment_data["payment_date"]).date(),
            receipt_number=payment_data["receipt_number"],
        )

        # Update member expiration
        member.expiration_date = datetime.fromisoformat(
            payment_data["new_expiration"]
        ).date()

        # Reactivate if inactive
        was_inactive = member.status == "inactive"
        if was_inactive:
            member.status = "active"
            member.date_inactivated = None

        member.save()

        return payment, was_inactive


class MemberService:
    """Service class for member-related business logic"""

    @staticmethod
    def get_suggested_ids(count=5):
        """
        Get suggested available member IDs.

        Args:
            count: Number of IDs to suggest (default: 5)

        Returns:
            tuple: (next_id, list_of_suggested_ids)
        """
        used_ids = set(
            Member.objects.filter(status="active", member_id__isnull=False).values_list(
                "member_id", flat=True
            )
        )

        suggested_ids = []
        for id_num in range(1, 1001):  # Search range 1-1000
            if id_num not in used_ids:
                suggested_ids.append(id_num)
                if len(suggested_ids) >= count:
                    break

        next_member_id = suggested_ids[0] if suggested_ids else 1
        return next_member_id, suggested_ids

    @staticmethod
    def create_member(member_data):
        """
        Create member with validation.

        Args:
            member_data: Dict with member details:
                - member_type_id: MemberType ID
                - first_name, last_name, email
                - member_id: Member ID (integer)
                - milestone_date: ISO format string
                - date_joined: ISO format string
                - home_address, home_city, home_state, home_zip, home_phone
                - initial_expiration: ISO format string

        Returns:
            Member instance
        """
        member_type = MemberType.objects.get(pk=member_data["member_type_id"])

        member = Member.objects.create_new_member(
            first_name=member_data["first_name"],
            last_name=member_data["last_name"],
            email=member_data["email"],
            member_type=member_type,
            milestone_date=datetime.fromisoformat(member_data["milestone_date"]).date(),
            date_joined=datetime.fromisoformat(member_data["date_joined"]).date(),
            home_address=member_data["home_address"],
            home_city=member_data["home_city"],
            home_state=member_data["home_state"],
            home_zip=member_data["home_zip"],
            home_phone=member_data["home_phone"],
            expiration_date=datetime.fromisoformat(
                member_data["initial_expiration"]
            ).date(),
            member_id=member_data["member_id"],
        )

        return member

    @staticmethod
    def check_duplicate_members(first_name, last_name, email, phone):
        """
        Check for existing members matching name, phone, or email.

        Args:
            first_name: First name to check
            last_name: Last name to check
            email: Email to check (can be empty)
            phone: Phone number to check (can be empty, database field is home_phone)

        Returns:
            List of dicts with keys: 'member', 'match_reason', 'match_text'
        """
        matches = []

        # Check name combination (case-insensitive)
        name_matches = Member.objects.filter(
            first_name__iexact=first_name, last_name__iexact=last_name
        )
        for member in name_matches:
            matches.append(
                {
                    "member": member,
                    "match_reason": "name",
                    "match_text": f"{first_name} {last_name}",
                }
            )

        # Check phone (if provided) - database field is home_phone
        if phone:
            phone_matches = Member.objects.filter(home_phone=phone)
            for member in phone_matches:
                # Avoid duplicates if already matched by name
                if not any(m["member"].pk == member.pk for m in matches):
                    matches.append(
                        {"member": member, "match_reason": "phone", "match_text": phone}
                    )

        # Check email (if provided)
        if email:
            email_matches = Member.objects.filter(email__iexact=email)
            for member in email_matches:
                # Avoid duplicates if already matched by name/phone
                if not any(m["member"].pk == member.pk for m in matches):
                    matches.append(
                        {"member": member, "match_reason": "email", "match_text": email}
                    )

        return matches
