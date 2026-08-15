from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from ..models import Member, Payment, PaymentMethod
from ..services import PaymentService
from ..utils import ensure_end_of_month


def _back_from_payment(member_uuid=None):
    if member_uuid:
        return redirect("members:member_detail", member_uuid=member_uuid)
    return redirect("members:search")


@staff_member_required
def add_payment_view(request):
    """Payment entry workflow with member search, form, and confirmation"""

    # Get workflow step
    step = request.GET.get("step", "search")
    member_uuid = request.GET.get("member", "")

    # If member UUID is provided, skip search and go to form
    if member_uuid and step == "search":
        try:
            member = get_object_or_404(Member, member_uuid=member_uuid)
            # Redirect to form step with the member
            return redirect(f"{request.path}?step=form&member={member_uuid}")
        except:  # noqa: E722
            return redirect("members:search")

    if step == "search":
        return redirect("members:search")

    elif step == "form":
        # Step 2: Payment Form (member selected)
        if not member_uuid:
            messages.error(request, "Please select a member first.")
            return redirect("members:search")

        member = get_object_or_404(Member, member_uuid=member_uuid)

        # Don't allow payments for deceased members
        if member.status == "deceased":
            messages.error(request, "Cannot add payments for deceased members.")
            return _back_from_payment(member.member_uuid)

        # Check if this is a Life member - no payments allowed
        if member.member_type and member.member_type.member_type == "Life":
            context = {
                "step": "life_member",
                "member": member,
            }
            return render(request, "members/add_payment.html", context)

        payment_methods = PaymentMethod.objects.all().order_by("payment_method")

        # Auto-populate suggested payment amount (monthly dues)
        suggested_amount = (
            member.member_type.member_dues if member.member_type else Decimal("0.00")
        )

        # Don't calculate new expiration here - it will be calculated dynamically
        # based on the actual payment amount entered by the user

        # Build duration options from member type discount fields
        duration_options = []
        mt = member.member_type
        if mt and mt.six_month_charge is not None:
            duration_options = [
                {"key": "monthly", "label": "Monthly", "charge_months": 1, "duration_months": 1},
                {"key": "6month", "label": "6 Months", "charge_months": mt.six_month_charge, "duration_months": mt.six_month_duration},
                {"key": "yearly", "label": "Year + 1 Bonus Month", "charge_months": mt.yearly_charge, "duration_months": mt.yearly_duration},
            ]

        saved = {}
        if request.GET.get("edit"):
            saved = request.session.get("payment_data", {})
        else:
            request.session.pop("payment_data", None)

        context = {
            "step": "form",
            "member": member,
            "payment_methods": payment_methods,
            "suggested_amount": suggested_amount,
            "duration_options": duration_options,
            "today": date.today(),
            "saved_amount": saved.get("amount"),
            "saved_payment_date": saved.get("payment_date"),
            "saved_payment_method_id": saved.get("payment_method_id"),
            "saved_receipt_number": saved.get("receipt_number") or "",
            "saved_duration": saved.get("payment_duration", "monthly"),
            "saved_months": saved.get("num_months", "1"),
            "saved_new_expiration": saved.get("new_expiration", ""),
        }
        return render(request, "members/add_payment.html", context)

    elif step == "confirm":
        # Step 3: Confirmation (form submitted)
        if request.method == "POST":
            member_uuid = request.POST.get("member_uuid")
            amount = request.POST.get("amount")
            payment_date = request.POST.get("payment_date")
            payment_method_id = request.POST.get("payment_method")
            receipt_number = request.POST.get("receipt_number", "").strip()
            payment_duration = request.POST.get("payment_duration", "monthly")
            num_months = request.POST.get("num_months", "1")

            # Validate form data
            try:
                member = get_object_or_404(Member, member_uuid=member_uuid)

                # Don't allow payments for deceased members
                if member.status == "deceased":
                    raise ValueError("Cannot add payments for deceased members")

                override_expiration = request.POST.get("override_expiration")

                payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
                if payment_date > date.today():
                    raise ValueError("Payment date cannot be in the future")
                payment_method = get_object_or_404(PaymentMethod, pk=payment_method_id)

                # Validate receipt number is provided
                if not receipt_number:
                    raise ValueError("Receipt number is required")

                # Resolve duration-based charge and expiration months
                mt = member.member_type
                duration_months = None
                if payment_duration == "6month" and mt and mt.six_month_charge:
                    amount = mt.member_dues * mt.six_month_charge
                    duration_months = mt.six_month_duration
                elif payment_duration == "yearly" and mt and mt.yearly_charge:
                    amount = mt.member_dues * mt.yearly_charge
                    duration_months = mt.yearly_duration
                else:
                    amount = Decimal(amount)

                # Calculate or use override expiration date
                override_expiration_date = None
                if override_expiration:
                    override_expiration_date = datetime.strptime(
                        override_expiration, "%Y-%m-%d"
                    ).date()
                    from ..utils import ensure_end_of_month

                    override_expiration_date = ensure_end_of_month(
                        override_expiration_date
                    )

                new_expiration = PaymentService.calculate_expiration(
                    member, amount, override_expiration_date, duration_months
                )

                # Store in session for final processing
                request.session["payment_data"] = {
                    "member_uuid": str(member_uuid),
                    "amount": str(amount),
                    "payment_date": payment_date.isoformat(),
                    "payment_method_id": payment_method_id,
                    "receipt_number": receipt_number,
                    "new_expiration": new_expiration.isoformat(),
                    "payment_duration": payment_duration,
                    "num_months": num_months,
                }

                # Check for duplicate receipt number (global)
                receipt_warnings = list(
                    Payment.objects.filter(receipt_number=receipt_number)
                    .select_related("member")
                    .values_list(
                        "member__first_name",
                        "member__last_name",
                        "date",
                        "amount",
                    )
                )

                # Check for same member + same date
                date_warnings = list(
                    Payment.objects.filter(member=member, date=payment_date)
                    .select_related("payment_method")
                    .values_list(
                        "receipt_number",
                        "amount",
                        "payment_method__payment_method",
                    )
                )

                context = {
                    "step": "confirm",
                    "member": member,
                    "amount": amount,
                    "payment_date": payment_date,
                    "payment_method": payment_method,
                    "receipt_number": receipt_number,
                    "current_expiration": member.expiration_date,
                    "new_expiration": new_expiration,
                    "receipt_warnings": receipt_warnings,
                    "date_warnings": date_warnings,
                }
                return render(request, "members/add_payment.html", context)

            except (ValueError, Member.DoesNotExist, PaymentMethod.DoesNotExist) as e:
                messages.error(request, f"Invalid payment data: {e}")
                # If we have a member_uuid, redirect back to form with member selected
                if member_uuid:
                    return redirect(f"/payments/add/?step=form&member={member_uuid}")
                else:
                    return redirect("members:search")

        else:
            messages.error(request, "Invalid request.")
            return redirect("members:search")

    elif step == "process":
        # Step 4: Final Processing
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            payment_data = request.session.get("payment_data")
            if not payment_data:
                messages.error(request, "Payment session expired. Please try again.")
                return redirect("members:search")

            try:
                # Get member and process payment using PaymentService
                member = get_object_or_404(
                    Member, member_uuid=payment_data["member_uuid"]
                )

                # Process payment using PaymentService
                payment, was_inactive = PaymentService.process_payment(
                    member, payment_data
                )

                # Clear session data
                if "payment_data" in request.session:
                    del request.session["payment_data"]

                # Create success message
                success_msg = f"Payment of ${payment.amount} successfully recorded for {member.full_name}. Membership expires {member.expiration_date.strftime('%B %d, %Y')}."
                if was_inactive:
                    success_msg += " Member status changed from Inactive to Active."

                messages.success(request, success_msg)
                return redirect("members:member_detail", member_uuid=member.member_uuid)

            except Exception as e:
                messages.error(request, f"Error processing payment: {e}")
                return _back_from_payment(payment_data.get("member_uuid"))
        else:
            # User cancelled or invalid request
            payment_data = request.session.pop("payment_data", None) or {}
            messages.info(request, "Payment cancelled.")
            return _back_from_payment(payment_data.get("member_uuid"))

    else:
        # Invalid step
        return redirect("members:search")


@staff_member_required
def edit_payment_view(request, payment_id):
    """Edit an existing payment's date, amount, payment method, and receipt number."""
    payment = get_object_or_404(
        Payment.objects.select_related("member", "payment_method", "member__member_type"),
        pk=payment_id,
    )
    member = payment.member

    if member.status == "deceased":
        messages.error(request, "Cannot edit payments for deceased members.")
        return redirect("members:member_detail", member_uuid=member.member_uuid)

    payment_methods = PaymentMethod.objects.all().order_by("payment_method")
    member_payments = member.payments.select_related("payment_method").order_by("-date")

    if request.method == "POST":
        payment_date = request.POST.get("payment_date", "").strip()
        amount = request.POST.get("amount", "").strip()
        payment_method_id = request.POST.get("payment_method", "").strip()
        receipt_number = request.POST.get("receipt_number", "").strip()
        new_expiration = request.POST.get("new_expiration_date", "").strip()

        errors = []

        # Validate date
        try:
            parsed_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
            if parsed_date > date.today():
                errors.append("Payment date cannot be in the future.")
        except (ValueError, TypeError):
            errors.append("Invalid payment date.")
            parsed_date = None

        # Validate new_expiration_date (optional)
        parsed_new_expiration = None
        if new_expiration:
            try:
                parsed_new_expiration = ensure_end_of_month(
                    datetime.strptime(new_expiration, "%Y-%m-%d").date()
                )
            except (ValueError, TypeError):
                errors.append("Invalid expiration date.")

        # Validate amount
        try:
            parsed_amount = Decimal(amount)
            if parsed_amount <= 0:
                errors.append("Amount must be greater than zero.")
        except (InvalidOperation, ValueError, TypeError):
            errors.append("Invalid payment amount.")
            parsed_amount = None

        # Validate payment method
        try:
            method = PaymentMethod.objects.get(pk=payment_method_id)
        except (PaymentMethod.DoesNotExist, ValueError):
            errors.append("Invalid payment method.")
            method = None

        # Validate receipt number
        if not receipt_number:
            errors.append("Receipt number is required.")

        if errors:
            context = {
                "payment": payment,
                "member": member,
                "payment_methods": payment_methods,
                "member_payments": member_payments,
                "errors": errors,
                "form_date": payment_date,
                "form_amount": amount,
                "form_method_id": payment_method_id,
                "form_receipt": receipt_number,
                "form_new_expiration": new_expiration,
            }
            return render(request, "members/edit_payment.html", context)

        payment.date = parsed_date
        payment.amount = parsed_amount
        payment.payment_method = method
        payment.receipt_number = receipt_number
        payment.new_expiration_date = parsed_new_expiration
        payment.save(update_fields=["date", "amount", "payment_method", "receipt_number", "new_expiration_date", "updated_at"])

        messages.success(
            request,
            f"Payment updated for {member.full_name} — ${parsed_amount} on {parsed_date.strftime('%B %d, %Y')}.",
        )
        return redirect("members:member_detail", member_uuid=member.member_uuid)

    context = {
        "payment": payment,
        "member": member,
        "payment_methods": payment_methods,
        "member_payments": member_payments,
    }
    return render(request, "members/edit_payment.html", context)
