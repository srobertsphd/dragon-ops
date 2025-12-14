from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.core.validators import EmailValidator, ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from datetime import datetime, date
from decimal import Decimal

from ..models import Member, MemberType, PaymentMethod, STATE_CHOICES
from ..utils import ensure_end_of_month
from ..services import MemberService, PaymentService


@login_required
def reactivate_member_view(request, member_uuid):
    """Redirect to add_member flow with reactivation context"""
    member = get_object_or_404(Member, member_uuid=member_uuid)

    if member.status != "inactive":
        messages.error(request, "Only inactive members can be reactivated.")
        return redirect("members:member_detail", member_uuid=member_uuid)

    # Clear any stale session data from previous reactivation attempts
    if "member_data" in request.session:
        del request.session["member_data"]
    if "payment_data" in request.session:
        del request.session["payment_data"]

    request.session["reactivate_member_uuid"] = str(member_uuid)
    return redirect("members:add_member")


@login_required
def member_detail_view(request, member_uuid):
    """Member detail page with payment history and optional date filtering"""
    member = get_object_or_404(Member, member_uuid=member_uuid)

    # Get payment history with optional date filtering
    payments_queryset = (
        member.payments.all().select_related("payment_method").order_by("-date")
    )

    # Apply date filters if provided
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            payments_queryset = payments_queryset.filter(date__gte=start_date_obj)
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            payments_queryset = payments_queryset.filter(date__lte=end_date_obj)
        except ValueError:
            pass

    # Paginate payment history (20 per page)
    paginator = Paginator(payments_queryset, 20)
    page_number = request.GET.get("page")
    payments = paginator.get_page(page_number)

    context = {
        "member": member,
        "payments": payments,
        "start_date": start_date,
        "end_date": end_date,
        "total_payments": payments_queryset.count(),
    }

    return render(request, "members/member_detail.html", context)


@staff_member_required
def edit_member_view(request, member_uuid=None):
    """Edit member page: search mode (member_uuid=None) or edit mode (member_uuid provided)"""
    if member_uuid is None:
        query = request.GET.get("q", "").strip()
        members = None
        if query:
            try:
                members = (
                    Member.objects.filter(status="active", member_id=int(query))
                    .select_related("member_type")
                    .order_by("last_name", "first_name")
                )
            except ValueError:
                members = (
                    Member.objects.filter(status="active")
                    .filter(
                        Q(first_name__icontains=query) | Q(last_name__icontains=query)
                    )
                    .select_related("member_type")
                    .order_by("last_name", "first_name")
                )
        return render(
            request,
            "members/edit_member.html",
            {"query": query, "members": members, "mode": "search"},
        )

    member = get_object_or_404(Member, member_uuid=member_uuid)
    if member.status != "active":
        messages.error(
            request,
            "Only active members can be edited. Use 'Reactivate Member' to reactivate an inactive member.",
        )
        return redirect("members:edit_member")

    if request.method == "GET":
        _, suggested_ids = MemberService.get_suggested_ids(count=50)
        if member.member_id and member.member_id not in suggested_ids:
            suggested_ids.insert(0, member.member_id)
        return render(
            request,
            "members/edit_member.html",
            {
                "member": member,
                "member_types": MemberType.objects.all(),
                "today": date.today(),
                "suggested_ids": suggested_ids[:50],
                "state_choices": STATE_CHOICES,
                "mode": "edit",
            },
        )

    # POST: Process form submission
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip()
    member_type_id = request.POST.get("member_type")
    member_id = request.POST.get("member_id")
    milestone_date = request.POST.get("milestone_date")
    skip_milestone = request.POST.get("skip_milestone") == "on"
    date_joined = request.POST.get("date_joined")
    expiration_date = request.POST.get("expiration_date") or request.POST.get(
        "override_expiration"
    )
    home_address = request.POST.get("home_address", "").strip()
    home_city = request.POST.get("home_city", "").strip()
    home_state = request.POST.get("home_state", "").strip()
    home_zip = request.POST.get("home_zip", "").strip()
    home_phone = request.POST.get("home_phone", "").strip()

    try:
        if not all([first_name, last_name, member_type_id, member_id, date_joined]):
            raise ValueError("Required fields are missing")
        if not skip_milestone and not milestone_date:
            raise ValueError(
                "Milestone date is required. Check 'Skip Milestone Date' if you don't want to provide one."
            )
        if not expiration_date:
            raise ValueError("Expiration date is required")

        if email:
            try:
                EmailValidator()(email)
            except ValidationError:
                raise ValueError("Please enter a valid email address")

        member_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "member_type_id": member_type_id,
            "member_id": int(member_id),
            "milestone_date": milestone_date if milestone_date else "",
            "date_joined": date_joined,
            "expiration_date": expiration_date,
            "home_address": home_address,
            "home_city": home_city,
            "home_state": home_state,
            "home_zip": home_zip,
            "home_phone": home_phone,
        }

        MemberService.update_member(member, member_data)

        messages.success(
            request,
            f"Member {member.full_name} (#{member.member_id}) updated successfully.",
        )
        return redirect("members:member_detail", member_uuid=member.member_uuid)

    except (ValueError, ValidationError, MemberType.DoesNotExist) as e:
        messages.error(request, str(e))
        _, suggested_ids = MemberService.get_suggested_ids(count=50)
        if member.member_id and member.member_id not in suggested_ids:
            suggested_ids.insert(0, member.member_id)
        return render(
            request,
            "members/edit_member.html",
            {
                "member": member,
                "member_types": MemberType.objects.all(),
                "today": date.today(),
                "suggested_ids": suggested_ids[:50],
                "state_choices": STATE_CHOICES,
                "mode": "edit",
                "member_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "member_type_id": member_type_id,
                    "member_id": member_id,
                    "milestone_date": milestone_date,
                    "date_joined": date_joined,
                    "expiration_date": expiration_date,
                    "home_address": home_address,
                    "home_city": home_city,
                    "home_state": home_state,
                    "home_zip": home_zip,
                    "home_phone": home_phone,
                },
            },
        )


@login_required
def add_member_view(request):
    """Add new member workflow with form, validation, and confirmation"""

    # Get workflow step
    step = request.GET.get("step", "form")

    # Clear stale session data only when starting a fresh form (not when navigating between steps)
    # Clear member_data and payment_data only on form step when it's a fresh start
    # Preserve session data when navigating back from other steps (e.g., from payment step)
    # Clear reactivate_member_uuid only if member_data exists (stale data scenario)
    # If reactivate_member_uuid exists without member_data, it's a fresh reactivation (will re-populate)
    # Check if this is a fresh start:
    # - Must be form step
    # - Must be GET request (not POST)
    # - Must not have "back" parameter (indicates navigating back)
    # - Must not have "reactivate" parameter (indicates reactivation flow)
    is_fresh_start = (
        step == "form"
        and request.method == "GET"  # Only clear on GET, not POST
        and not request.GET.get("back")  # "back" parameter indicates navigating back
        and not request.GET.get(
            "reactivate"
        )  # "reactivate" parameter indicates reactivation
    )

    if is_fresh_start:
        if "member_data" in request.session:
            del request.session["member_data"]
            # If member_data existed, also clear reactivate_member_uuid (it's stale)
            if "reactivate_member_uuid" in request.session:
                del request.session["reactivate_member_uuid"]
        if "payment_data" in request.session:
            del request.session["payment_data"]

    if step == "form":
        # Step 1: Member Form
        member_types = MemberType.objects.all()

        # Check for reactivation mode
        reactivate_uuid = request.session.get("reactivate_member_uuid")
        member_data = request.session.get("member_data", {})
        reactivate_member = None

        # Get next available member ID and suggestions
        next_member_id, suggested_ids = MemberService.get_suggested_ids(count=50)

        if reactivate_uuid and not member_data:
            # Pre-populate from inactive member
            reactivate_member = get_object_or_404(Member, member_uuid=reactivate_uuid)
            if reactivate_member.status != "inactive":
                messages.error(request, "Only inactive members can be reactivated.")
                del request.session["reactivate_member_uuid"]
                return redirect("members:member_detail", member_uuid=reactivate_uuid)

            # Check if preferred_member_id is available
            preferred_id = reactivate_member.preferred_member_id
            if (
                preferred_id
                and 1 <= preferred_id <= 999  # Validate range
                and Member.objects.is_member_id_available(preferred_id)
            ):
                # Preferred ID is available, use it
                member_id_to_use = preferred_id
            else:
                # Preferred ID taken, out of range, or doesn't exist, use next available
                member_id_to_use = next_member_id

            # Pre-populate member_data from inactive member
            member_data = {
                "first_name": reactivate_member.first_name,
                "last_name": reactivate_member.last_name,
                "email": reactivate_member.email,
                "member_type_id": str(reactivate_member.member_type.pk),
                "member_id": member_id_to_use,
                "milestone_date": reactivate_member.milestone_date.isoformat()
                if reactivate_member.milestone_date
                else "",
                "date_joined": date.today().isoformat(),  # Set to today for reactivation
                "home_address": reactivate_member.home_address,
                "home_city": reactivate_member.home_city,
                "home_state": reactivate_member.home_state,
                "home_zip": reactivate_member.home_zip,
                "home_phone": reactivate_member.home_phone,
            }
            request.session["member_data"] = member_data

        # If reactivating, add preferred_member_id to suggestions if available
        if reactivate_uuid:
            # Load reactivate_member if not already loaded
            if reactivate_member is None:
                reactivate_member = get_object_or_404(
                    Member, member_uuid=reactivate_uuid
                )

            # Check if preferred_member_id exists and is available
            preferred_id = reactivate_member.preferred_member_id
            if (
                preferred_id
                and 1 <= preferred_id <= 999  # Validate range
                and Member.objects.is_member_id_available(preferred_id)
                and preferred_id not in suggested_ids
            ):
                # Add preferred ID at the beginning of suggestions
                suggested_ids.insert(0, preferred_id)
                # Limit to 5 suggestions total
                suggested_ids = suggested_ids[:5]

        # Determine message type and text for ID restoration feedback
        id_message_type = None
        id_message = None
        if reactivate_uuid:
            # Load reactivate_member if not already loaded
            if reactivate_member is None:
                reactivate_member = get_object_or_404(
                    Member, member_uuid=reactivate_uuid
                )

            # Get the member ID that will be displayed in the field
            current_member_id = None
            if member_data and "member_id" in member_data:
                current_member_id = member_data["member_id"]
            else:
                # Use next_member_id as fallback (this is what would be shown)
                current_member_id = next_member_id

            # Determine message based on preferred ID status
            preferred_id = reactivate_member.preferred_member_id
            if preferred_id and 1 <= preferred_id <= 999:
                if current_member_id == preferred_id:
                    # Preferred ID was restored
                    id_message_type = "restored"
                    id_message = f"Your previous Member ID (#{preferred_id}) is available and will be restored."
                else:
                    # Preferred ID exists but wasn't used (taken or unavailable)
                    id_message_type = "unavailable"
                    id_message = f"Your previous Member ID (#{preferred_id}) is no longer available. A new ID (#{current_member_id}) has been selected."
            # If no preferred_id, no message (id_message_type stays None)

        context = {
            "step": "form",
            "member_types": member_types,
            "today": date.today(),
            "next_member_id": member_data.get("member_id", next_member_id)
            if member_data
            else next_member_id,
            "suggested_ids": suggested_ids,
            "member_data": member_data,
            "reactivate_member": reactivate_member if reactivate_uuid else None,
            "id_message_type": id_message_type,
            "id_message": id_message,
            "state_choices": STATE_CHOICES,
        }
        return render(request, "members/add_member.html", context)

    elif step == "confirm":
        # Step 2: Confirmation (form submitted)
        if request.method == "POST":
            # Get form data
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            email = request.POST.get("email", "").strip()
            member_type_id = request.POST.get("member_type")
            member_id = request.POST.get("member_id")
            milestone_date = request.POST.get("milestone_date")
            skip_milestone = request.POST.get("skip_milestone") == "on"
            date_joined = request.POST.get("date_joined")
            home_address = request.POST.get("home_address", "").strip()
            home_city = request.POST.get("home_city", "").strip()
            home_state = request.POST.get("home_state", "").strip()
            home_zip = request.POST.get("home_zip", "").strip()
            home_phone = request.POST.get("home_phone", "").strip()

            # Validate required fields
            try:
                if not first_name:
                    raise ValueError("First name is required")
                if not last_name:
                    raise ValueError("Last name is required")
                if not member_type_id:
                    raise ValueError("Member type is required")
                if not member_id:
                    raise ValueError("Member ID is required")
                if not date_joined:
                    raise ValueError("Date joined is required")
                if not skip_milestone and not milestone_date:
                    raise ValueError(
                        "Milestone date is required. Check 'Skip Milestone Date' if you don't want to provide one."
                    )

                # Validate email format if provided (email is optional)
                if email:
                    validator = EmailValidator()
                    try:
                        validator(email)
                    except ValidationError:
                        raise ValueError("Please enter a valid email address")

                # Validate member ID range and availability
                try:
                    member_id_int = int(member_id)
                except ValueError:
                    raise ValueError(
                        f"Member ID must be a number. You entered: '{member_id}'"
                    )

                # Validate range (1-999)
                if member_id_int < 1 or member_id_int > 999:
                    raise ValueError(
                        f"Member ID must be between 1 and 999. You entered: {member_id_int}"
                    )

                # Validate member ID is available
                if Member.objects.filter(
                    status="active", member_id=member_id_int
                ).exists():
                    raise ValueError(f"Member ID {member_id_int} is already in use")

                # Validate member type exists
                member_type = get_object_or_404(MemberType, pk=member_type_id)

                # Parse and validate dates
                milestone_date_obj = None
                if milestone_date:
                    milestone_date_obj = datetime.strptime(
                        milestone_date, "%Y-%m-%d"
                    ).date()
                    # Validate milestone date is not in the future
                    if milestone_date_obj > date.today():
                        raise ValueError("Milestone date cannot be in the future")

                date_joined_obj = datetime.strptime(date_joined, "%Y-%m-%d").date()

                # Validate date joined is not in the future
                if date_joined_obj > date.today():
                    raise ValueError("Date joined cannot be in the future")

                # Check if reactivating
                reactivate_uuid = request.session.get("reactivate_member_uuid")
                reactivate_member = None
                duplicate_members = []

                if reactivate_uuid:
                    # Reactivation mode - skip duplicate detection, load reactivate member info
                    reactivate_member = get_object_or_404(
                        Member, member_uuid=reactivate_uuid
                    )
                else:
                    # New member mode - check for duplicates
                    duplicate_members = MemberService.check_duplicate_members(
                        first_name, last_name, email, home_phone
                    )

                # Store in session for final processing
                request.session["member_data"] = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "member_type_id": member_type_id,
                    "member_id": member_id_int,
                    "milestone_date": milestone_date_obj.isoformat()
                    if milestone_date_obj
                    else "",
                    "date_joined": date_joined_obj.isoformat(),
                    "home_address": home_address,
                    "home_city": home_city,
                    "home_state": home_state,
                    "home_zip": home_zip,
                    "home_phone": home_phone,
                }

                context = {
                    "step": "confirm",
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "member_type": member_type,
                    "member_id": member_id_int,
                    "milestone_date": milestone_date_obj,
                    "date_joined": date_joined_obj,
                    "home_address": home_address,
                    "home_city": home_city,
                    "home_state": home_state,
                    "home_zip": home_zip,
                    "home_phone": home_phone,
                    "duplicate_members": duplicate_members,
                    "reactivate_member": reactivate_member,
                    "state_choices": STATE_CHOICES,
                }
                return render(request, "members/add_member.html", context)

            except (ValueError, MemberType.DoesNotExist) as e:
                messages.error(request, str(e))
                # Render form again with preserved data instead of redirecting
                member_types = MemberType.objects.all()
                next_member_id, suggested_ids = MemberService.get_suggested_ids(
                    count=50
                )

                # Preserve form data in context
                context = {
                    "step": "form",
                    "member_types": member_types,
                    "today": date.today(),
                    "next_member_id": next_member_id,
                    "suggested_ids": suggested_ids,
                    "member_data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "member_type_id": member_type_id,
                        "member_id": member_id,  # Preserve the entered ID
                        "milestone_date": milestone_date,
                        "date_joined": date_joined,
                        "home_address": home_address,
                        "home_city": home_city,
                        "home_state": home_state,
                        "home_zip": home_zip,
                        "home_phone": home_phone,
                    },
                    "reactivate_member": None,
                    "state_choices": STATE_CHOICES,
                }
                return render(request, "members/add_member.html", context)
        else:
            # Handle GET request (navigating back from payment step)
            member_data = request.session.get("member_data")
            if not member_data:
                messages.error(request, "Member session expired. Please try again.")
                return redirect("members:add_member")

            try:
                # Parse dates from session (stored as ISO strings)
                milestone_date_obj = None
                if member_data.get("milestone_date"):
                    milestone_date_obj = datetime.strptime(
                        member_data["milestone_date"], "%Y-%m-%d"
                    ).date()

                date_joined_obj = datetime.strptime(
                    member_data["date_joined"], "%Y-%m-%d"
                ).date()

                # Get member type
                member_type = get_object_or_404(
                    MemberType, pk=member_data["member_type_id"]
                )

                # Check if reactivating
                reactivate_uuid = request.session.get("reactivate_member_uuid")
                reactivate_member = None
                duplicate_members = []

                if reactivate_uuid:
                    reactivate_member = get_object_or_404(
                        Member, member_uuid=reactivate_uuid
                    )
                else:
                    # Check for duplicates
                    duplicate_members = MemberService.check_duplicate_members(
                        member_data["first_name"],
                        member_data["last_name"],
                        member_data.get("email", ""),
                        member_data.get("home_phone", ""),
                    )

                # Reconstruct confirmation context
                context = {
                    "step": "confirm",
                    "first_name": member_data["first_name"],
                    "last_name": member_data["last_name"],
                    "email": member_data.get("email", ""),
                    "member_type": member_type,
                    "member_id": member_data["member_id"],
                    "milestone_date": milestone_date_obj,
                    "date_joined": date_joined_obj,
                    "home_address": member_data.get("home_address", ""),
                    "home_city": member_data.get("home_city", ""),
                    "home_state": member_data.get("home_state", ""),
                    "home_zip": member_data.get("home_zip", ""),
                    "home_phone": member_data.get("home_phone", ""),
                    "duplicate_members": duplicate_members,
                    "reactivate_member": reactivate_member,
                    "state_choices": STATE_CHOICES,
                }
                return render(request, "members/add_member.html", context)

            except (KeyError, ValueError, MemberType.DoesNotExist) as e:
                messages.error(request, f"Invalid session data: {e}")
                return redirect("members:add_member")

    elif step == "payment":
        # Step 3: Payment Form (for new member)
        member_data = request.session.get("member_data")
        if not member_data:
            messages.error(request, "Member session expired. Please try again.")
            return redirect("members:add_member")

        if request.method == "GET":
            # Show payment form
            try:
                member_type = get_object_or_404(
                    MemberType, pk=member_data["member_type_id"]
                )
                payment_methods = PaymentMethod.objects.all().order_by("payment_method")

                # Calculate suggested payment amount
                suggested_amount = (
                    PaymentService.calculate_suggested_payment_for_new_member(
                        member_type
                    )
                )

                # Check if reactivating
                reactivate_uuid = request.session.get("reactivate_member_uuid")
                reactivate_member = None
                if reactivate_uuid:
                    reactivate_member = get_object_or_404(
                        Member, member_uuid=reactivate_uuid
                    )

                context = {
                    "step": "payment",
                    "member_type": member_type,
                    "payment_methods": payment_methods,
                    "suggested_amount": suggested_amount,
                    "today": date.today(),
                    "reactivate_member": reactivate_member,
                }
                return render(request, "members/add_member.html", context)

            except (MemberType.DoesNotExist, KeyError) as e:
                messages.error(request, f"Invalid member data: {e}")
                return redirect("members:add_member")

        elif request.method == "POST":
            # Handle payment form submission
            try:
                # Get payment form data
                amount = request.POST.get("amount")
                payment_date = request.POST.get("payment_date")
                payment_method_id = request.POST.get("payment_method")
                receipt_number = request.POST.get("receipt_number", "").strip()

                # Validate payment fields
                if not amount:
                    raise ValueError("Payment amount is required")
                if not payment_date:
                    raise ValueError("Payment date is required")
                if not payment_method_id:
                    raise ValueError("Payment method is required")
                if not receipt_number:
                    raise ValueError("Receipt number is required")

                # Get member_type from session
                member_type = get_object_or_404(
                    MemberType, pk=member_data["member_type_id"]
                )

                # Parse and validate
                amount = Decimal(amount)
                payment_date_obj = datetime.strptime(payment_date, "%Y-%m-%d").date()
                payment_method = get_object_or_404(PaymentMethod, pk=payment_method_id)

                # Check for override expiration (from month/year dropdowns via JavaScript)
                override_expiration = request.POST.get("override_expiration")

                # Calculate expiration date using PaymentService
                override_expiration_date = None
                if override_expiration:
                    override_expiration_date = datetime.strptime(
                        override_expiration, "%Y-%m-%d"
                    ).date()
                    override_expiration_date = ensure_end_of_month(
                        override_expiration_date
                    )

                new_expiration = PaymentService.calculate_expiration_for_new_member(
                    member_type, amount, payment_date_obj, override_expiration_date
                )

                # Store payment_data in session
                request.session["payment_data"] = {
                    "amount": str(amount),
                    "payment_date": payment_date_obj.isoformat(),
                    "payment_method_id": payment_method_id,
                    "receipt_number": receipt_number,
                    "new_expiration": new_expiration.isoformat(),
                }

                # Check if reactivating
                reactivate_uuid = request.session.get("reactivate_member_uuid")
                reactivate_member = None
                if reactivate_uuid:
                    reactivate_member = get_object_or_404(
                        Member, member_uuid=reactivate_uuid
                    )

                # Show payment confirmation
                context = {
                    "step": "payment_confirm",
                    "amount": amount,
                    "payment_date": payment_date_obj,
                    "payment_method": payment_method,
                    "receipt_number": receipt_number,
                    "new_expiration": new_expiration,
                    "reactivate_member": reactivate_member,
                }
                return render(request, "members/add_member.html", context)

            except (
                ValueError,
                PaymentMethod.DoesNotExist,
                MemberType.DoesNotExist,
            ) as e:
                messages.error(request, f"Invalid payment data: {e}")
                # Redirect back to payment form
                return redirect("members:add_member?step=payment")
        else:
            messages.error(request, "Invalid request.")
            return redirect("members:add_member")

    elif step == "process":
        # Step 4: Final Processing - Create member and payment
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            member_data = request.session.get("member_data")
            payment_data = request.session.get("payment_data")
            reactivate_uuid = request.session.get("reactivate_member_uuid")

            if not member_data:
                messages.error(request, "Member session expired. Please try again.")
                return redirect("members:add_member")

            if not payment_data:
                messages.error(request, "Payment session expired. Please try again.")
                return redirect("members:add_member")

            try:
                # Check if reactivation mode
                if reactivate_uuid:
                    # Update existing inactive member
                    member = get_object_or_404(Member, member_uuid=reactivate_uuid)
                    if member.status != "inactive":
                        messages.error(request, "Member is no longer inactive.")
                        return redirect(
                            "members:member_detail", member_uuid=reactivate_uuid
                        )

                    # Get member type
                    member_type = get_object_or_404(
                        MemberType, pk=member_data["member_type_id"]
                    )

                    # Handle member ID - preserve if available, otherwise use next available
                    requested_member_id = member_data["member_id"]
                    if (
                        Member.objects.filter(
                            status="active", member_id=requested_member_id
                        )
                        .exclude(member_uuid=member.member_uuid)
                        .exists()
                    ):
                        # Requested ID is taken by another member, use next available
                        next_member_id, _ = MemberService.get_suggested_ids(count=1)
                        member.member_id = next_member_id
                    else:
                        # Requested ID is available, use it
                        member.member_id = requested_member_id

                    # Update all fields
                    member.first_name = member_data["first_name"]
                    member.last_name = member_data["last_name"]
                    member.email = member_data["email"]
                    member.member_type = member_type
                    member.milestone_date = (
                        datetime.fromisoformat(member_data["milestone_date"]).date()
                        if member_data.get("milestone_date")
                        else None
                    )
                    member.date_joined = date.today()  # Set to today for reactivation
                    member.home_address = member_data["home_address"]
                    member.home_city = member_data["home_city"]
                    member.home_state = member_data["home_state"]
                    member.home_zip = member_data["home_zip"]
                    member.home_phone = member_data["home_phone"]
                    member.expiration_date = datetime.fromisoformat(
                        payment_data["new_expiration"]
                    ).date()
                    member.status = "active"
                    member.save()

                    # Create payment record
                    payment, was_inactive = PaymentService.process_payment(
                        member, payment_data
                    )

                    # Clear session data
                    if "member_data" in request.session:
                        del request.session["member_data"]
                    if "payment_data" in request.session:
                        del request.session["payment_data"]
                    if "reactivate_member_uuid" in request.session:
                        del request.session["reactivate_member_uuid"]

                    success_msg = f"Member {member.full_name} (#{member.member_id}) successfully reactivated with initial payment of ${payment.amount}. Membership expires {member.expiration_date.strftime('%B %d, %Y')}."
                    messages.success(request, success_msg)
                    return redirect(
                        "members:member_detail", member_uuid=member.member_uuid
                    )
                else:
                    # Normal flow - create new member
                    member_data["initial_expiration"] = payment_data["new_expiration"]
                    member = MemberService.create_member(member_data)
                    payment, was_inactive = PaymentService.process_payment(
                        member, payment_data
                    )

                    # Clear session data
                    if "member_data" in request.session:
                        del request.session["member_data"]
                    if "payment_data" in request.session:
                        del request.session["payment_data"]

                    success_msg = f"Member {member.full_name} (#{member.member_id}) successfully created with initial payment of ${payment.amount}. Membership expires {member.expiration_date.strftime('%B %d, %Y')}."
                    messages.success(request, success_msg)
                    return redirect("members:search")

            except Exception as e:
                messages.error(request, f"Error processing member and payment: {e}")
                return redirect("members:add_member")
        else:
            # User cancelled or invalid request
            if "member_data" in request.session:
                del request.session["member_data"]
            if "payment_data" in request.session:
                del request.session["payment_data"]
            if "reactivate_member_uuid" in request.session:
                del request.session["reactivate_member_uuid"]
            messages.info(request, "Member creation cancelled.")
            return redirect("members:add_member")

    else:
        # Invalid step
        return redirect("members:add_member")
