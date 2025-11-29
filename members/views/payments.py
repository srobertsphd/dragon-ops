from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime, date
from decimal import Decimal

from ..models import Member, PaymentMethod
from ..services import PaymentService


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
            # If invalid UUID, continue with search
            pass

    if step == "search":
        # Step 1: Member Search
        query = request.GET.get("q", "").strip()
        members = None

        if query:
            try:
                # Try to parse as member ID
                member_id = int(query)
                members = Member.objects.filter(member_id=member_id).exclude(
                    status="deceased"
                )
            except ValueError:
                # Search by name
                members = (
                    Member.objects.filter(
                        Q(first_name__icontains=query) | Q(last_name__icontains=query)
                    )
                    .exclude(status="deceased")
                    .select_related("member_type")
                    .order_by("last_name", "first_name")
                )

        context = {
            "step": "search",
            "query": query,
            "members": members,
        }
        return render(request, "members/add_payment.html", context)

    elif step == "form":
        # Step 2: Payment Form (member selected)
        if not member_uuid:
            messages.error(request, "Please select a member first.")
            return redirect("members:add_payment")

        member = get_object_or_404(Member, member_uuid=member_uuid)

        # Don't allow payments for deceased members
        if member.status == "deceased":
            messages.error(request, "Cannot add payments for deceased members.")
            return redirect("members:add_payment")

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

        context = {
            "step": "form",
            "member": member,
            "payment_methods": payment_methods,
            "suggested_amount": suggested_amount,
            "today": date.today(),
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

            # Validate form data
            try:
                member = get_object_or_404(Member, member_uuid=member_uuid)

                # Don't allow payments for deceased members
                if member.status == "deceased":
                    raise ValueError("Cannot add payments for deceased members")

                # Check for date override
                override_expiration = request.POST.get("override_expiration")

                amount = Decimal(amount)

                payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
                payment_method = get_object_or_404(PaymentMethod, pk=payment_method_id)

                # Validate receipt number is provided
                if not receipt_number:
                    raise ValueError("Receipt number is required")

                # Calculate or use override expiration date using PaymentService
                override_expiration_date = None
                if override_expiration:
                    override_expiration_date = datetime.strptime(
                        override_expiration, "%Y-%m-%d"
                    ).date()

                new_expiration = PaymentService.calculate_expiration(
                    member, amount, override_expiration_date
                )

                # Store in session for final processing
                request.session["payment_data"] = {
                    "member_uuid": str(member_uuid),
                    "amount": str(amount),
                    "payment_date": payment_date.isoformat(),
                    "payment_method_id": payment_method_id,
                    "receipt_number": receipt_number,
                    "new_expiration": new_expiration.isoformat(),
                }

                context = {
                    "step": "confirm",
                    "member": member,
                    "amount": amount,
                    "payment_date": payment_date,
                    "payment_method": payment_method,
                    "receipt_number": receipt_number,
                    "current_expiration": member.expiration_date,
                    "new_expiration": new_expiration,
                }
                return render(request, "members/add_payment.html", context)

            except (ValueError, Member.DoesNotExist, PaymentMethod.DoesNotExist) as e:
                messages.error(request, f"Invalid payment data: {e}")
                # If we have a member_uuid, redirect back to form with member selected
                if member_uuid:
                    return redirect(f"/payments/add/?step=form&member={member_uuid}")
                else:
                    return redirect("members:add_payment")

        else:
            messages.error(request, "Invalid request.")
            return redirect("members:add_payment")

    elif step == "process":
        # Step 4: Final Processing
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            payment_data = request.session.get("payment_data")
            if not payment_data:
                messages.error(request, "Payment session expired. Please try again.")
                return redirect("members:add_payment")

            try:
                # Get member and process payment using PaymentService
                member = get_object_or_404(
                    Member, member_uuid=payment_data["member_uuid"]
                )

                # Check if override expiration was changed on confirmation page
                override_expiration = request.POST.get("override_expiration")
                if override_expiration:
                    # Recalculate expiration with override date
                    override_expiration_date = datetime.strptime(
                        override_expiration, "%Y-%m-%d"
                    ).date()
                    amount = Decimal(payment_data["amount"])
                    new_expiration = PaymentService.calculate_expiration(
                        member, amount, override_expiration_date
                    )
                    # Update payment_data with new expiration
                    payment_data["new_expiration"] = new_expiration.isoformat()

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
                return redirect("members:add_payment")
        else:
            # User cancelled or invalid request
            if "payment_data" in request.session:
                del request.session["payment_data"]
            messages.info(request, "Payment cancelled.")
            return redirect("members:add_payment")

    else:
        # Invalid step
        return redirect("members:add_payment")
