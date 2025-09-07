from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from datetime import datetime, date
from decimal import Decimal
import calendar

from .models import Member, Payment, PaymentMethod, MemberType


def ensure_end_of_month(date):
    """Force date to be the last day of its month"""
    last_day = calendar.monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def add_months_to_date(date, months):
    """Add months to a date and return the last day of the resulting month

    Examples:
    - Current expiration: Mar 15, 2025 + 1 month = Mar 31, 2025
    - Current expiration: Jan 31, 2025 + 1 month = Feb 28, 2025 (or Feb 29 in leap year)
    - Current expiration: Dec 15, 2024 + 2 months = Feb 29, 2025

    This ensures all memberships expire at the end of the month regardless of payment date.
    """
    # Calculate the target year and month
    month = date.month - 1 + months
    year = date.year + month // 12
    month = month % 12 + 1

    # Get the last day of the target month
    last_day = calendar.monthrange(year, month)[1]

    return date.replace(year=year, month=month, day=last_day)


@staff_member_required
def landing_view(request):
    """Landing page with system overview"""
    return render(request, "members/landing.html")


@staff_member_required
def search_view(request):
    """Simple member search page with alphabet browsing and status filtering"""
    query = request.GET.get("q", "").strip()
    browse_range = request.GET.get("browse", "").strip()
    status_filter = request.GET.get("status", "all").strip()
    members = None

    # Get quick stats for the search page
    active_members_count = Member.objects.filter(status="active").count()
    total_payments_count = Payment.objects.count()

    # Calculate available IDs (1-1000 range)
    used_ids = set(
        Member.objects.filter(status="active", member_id__isnull=False).values_list(
            "member_id", flat=True
        )
    )
    available_ids_count = 1000 - len(used_ids)

    # Start with base queryset and apply status filter
    base_queryset = Member.objects.select_related("member_type")

    # Apply status filter
    if status_filter == "active":
        base_queryset = base_queryset.filter(status="active")
    elif status_filter == "inactive":
        base_queryset = base_queryset.filter(status="inactive")
    # "all" or any other value shows all members (no additional filter)

    # Handle alphabet browsing
    if browse_range:
        # Define the letter ranges
        range_mapping = {
            "A-C": ["A", "B", "C"],
            "D-F": ["D", "E", "F"],
            "G-I": ["G", "H", "I"],
            "J-L": ["J", "K", "L"],
            "M-O": ["M", "N", "O"],
            "P-R": ["P", "Q", "R"],
            "S-U": ["S", "T", "U"],
            "V-Z": ["V", "W", "X", "Y", "Z"],
        }

        if browse_range in range_mapping:
            letters = range_mapping[browse_range]
            # Create Q objects for each letter in the range
            letter_filters = Q()
            for letter in letters:
                letter_filters |= Q(last_name__istartswith=letter)

            members = base_queryset.filter(letter_filters).order_by(
                "last_name", "first_name"
            )

    # Perform search if query provided (takes precedence over browse)
    elif query:
        try:
            # Try to parse as member ID
            member_id = int(query)
            members = base_queryset.filter(member_id=member_id)
        except ValueError:
            # Search by name
            members = base_queryset.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).order_by("last_name", "first_name")

    context = {
        "query": query,
        "browse_range": browse_range,
        "status_filter": status_filter,
        "members": members,
        "active_members_count": active_members_count,
        "total_payments_count": total_payments_count,
        "available_ids_count": available_ids_count,
    }

    return render(request, "members/search.html", context)


@staff_member_required
def member_detail_view(request, member_uuid):
    """Member detail page with payment history and optional date filtering"""
    member = get_object_or_404(Member, member_uuid=member_uuid)

    # Get payment history with optional date filtering
    payments_queryset = (
        Payment.objects.filter(member=member)
        .select_related("payment_method")
        .order_by("-date")
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

                # Calculate or use override expiration date
                if override_expiration:
                    # Use selected override date (already end of month from dropdown)
                    new_expiration = datetime.strptime(
                        override_expiration, "%Y-%m-%d"
                    ).date()
                else:
                    # Calculate new expiration date based on payment amount
                    # Examples:
                    # - $30 payment / $30 monthly dues = 1 month paid
                    # - $60 payment / $30 monthly dues = 2 months paid
                    # - $15 payment / $30 monthly dues = 0.5 months = 0 months (rounded down)
                    if member.member_type and member.member_type.member_dues > 0:
                        # Calculate how many months the payment covers
                        # Example: $60 payment / $30 monthly dues = 2 months
                        months_paid = float(amount) / float(
                            member.member_type.member_dues
                        )
                        total_months_to_add = int(months_paid)
                        new_expiration = add_months_to_date(
                            member.expiration_date, total_months_to_add
                        )
                    else:
                        # Default to 1 month if no member type or dues
                        new_expiration = add_months_to_date(member.expiration_date, 1)

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
                # Get member and create payment
                member = get_object_or_404(
                    Member, member_uuid=payment_data["member_uuid"]
                )
                payment_method = get_object_or_404(
                    PaymentMethod, pk=payment_data["payment_method_id"]
                )

                # Create the payment record
                payment = Payment.objects.create(
                    member=member,
                    payment_method=payment_method,
                    amount=Decimal(payment_data["amount"]),
                    date=datetime.fromisoformat(payment_data["payment_date"]).date(),
                    receipt_number=payment_data["receipt_number"],
                )

                # Update member expiration date and reactivate if inactive
                member.expiration_date = datetime.fromisoformat(
                    payment_data["new_expiration"]
                ).date()

                # If member is inactive, reactivate them when they make a payment
                was_inactive = member.status == "inactive"
                if was_inactive:
                    member.status = "active"
                    member.date_inactivated = None

                member.save()

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


@staff_member_required
def current_members_report_view(request):
    """Generate current members report with payment history"""

    # Get all active members with their last 3 payments in one query
    active_members = (
        Member.objects.filter(status="active")
        .select_related("member_type")
        .prefetch_related(
            Prefetch(
                "payments",
                queryset=Payment.objects.select_related("payment_method").order_by(
                    "-date"
                ),
                to_attr="recent_payments",
            )
        )
        .order_by("last_name", "first_name")
    )

    # Separate regular members and life members
    regular_members = []
    life_members = []

    for member in active_members:
        # Get last 3 payments (already prefetched)
        recent_payments = (
            member.recent_payments[:3] if hasattr(member, "recent_payments") else []
        )

        member_data = {"member": member, "payments": recent_payments}

        # Separate by member type
        if member.member_type and member.member_type.member_type.lower() == "life":
            life_members.append(member_data)
        else:
            regular_members.append(member_data)

    context = {
        "regular_members": regular_members,
        "life_members": life_members,
        "report_date": date.today(),
        "total_regular": len(regular_members),
        "total_life": len(life_members),
        "total_members": len(regular_members) + len(life_members),
    }

    # Check if PDF is requested
    if request.GET.get("format") == "pdf":
        return generate_members_pdf(request, context)

    # Otherwise return HTML version for preview
    return render(request, "members/reports/current_members.html", context)


def generate_members_pdf(request, context):
    """Generate PDF version of current members report"""
    try:
        from weasyprint import HTML, CSS
        from django.template.loader import render_to_string

        # Render HTML template
        html_string = render_to_string(
            "members/reports/current_members_pdf.html", context
        )

        # Create PDF
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        # Return PDF response
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="current_members_{context["report_date"].strftime("%Y_%m_%d")}.pdf"'
        )
        return response

    except ImportError as e:
        # WeasyPrint not installed, return HTML version with error message
        from django.contrib import messages

        messages.error(
            request,
            f"PDF generation not available. Install WeasyPrint for PDF reports. Error: {e}",
        )
        return render(request, "members/reports/current_members.html", context)

    except Exception as e:
        # Other PDF generation errors
        from django.contrib import messages

        messages.error(request, f"Error generating PDF: {e}")
        return render(request, "members/reports/current_members.html", context)


@staff_member_required
def add_member_view(request):
    """Add new member workflow with form, validation, and confirmation"""

    # Get workflow step
    step = request.GET.get("step", "form")

    if step == "form":
        # Step 1: Member Form
        member_types = MemberType.objects.all()

        # Get next available member ID and suggestions efficiently
        # Get all used member IDs in one query
        used_ids = set(
            Member.objects.filter(status="active", member_id__isnull=False).values_list(
                "member_id", flat=True
            )
        )

        # Find next 5 available IDs efficiently
        suggested_ids = []
        for id_num in range(1, 1001):  # Search range 1-1000
            if id_num not in used_ids:
                suggested_ids.append(id_num)
                if len(suggested_ids) >= 5:
                    break

        next_member_id = suggested_ids[0] if suggested_ids else 1

        context = {
            "step": "form",
            "member_types": member_types,
            "today": date.today(),
            "next_member_id": next_member_id,
            "suggested_ids": suggested_ids,
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
                if not milestone_date:
                    raise ValueError("Milestone date is required")
                if not date_joined:
                    raise ValueError("Date joined is required")

                # Validate member ID is available
                member_id_int = int(member_id)
                if Member.objects.filter(
                    status="active", member_id=member_id_int
                ).exists():
                    raise ValueError(f"Member ID {member_id_int} is already in use")

                # Validate member type exists
                member_type = get_object_or_404(MemberType, pk=member_type_id)

                # Parse and validate dates
                milestone_date_obj = datetime.strptime(
                    milestone_date, "%Y-%m-%d"
                ).date()
                date_joined_obj = datetime.strptime(date_joined, "%Y-%m-%d").date()

                # Calculate initial expiration date (end of current month + member type months)
                today = date.today()
                current_month_end = ensure_end_of_month(today)
                initial_expiration = add_months_to_date(
                    current_month_end, member_type.num_months
                )

                # Store in session for final processing
                request.session["member_data"] = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "member_type_id": member_type_id,
                    "member_id": member_id_int,
                    "milestone_date": milestone_date_obj.isoformat(),
                    "date_joined": date_joined_obj.isoformat(),
                    "home_address": home_address,
                    "home_city": home_city,
                    "home_state": home_state,
                    "home_zip": home_zip,
                    "home_phone": home_phone,
                    "initial_expiration": initial_expiration.isoformat(),
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
                    "initial_expiration": initial_expiration,
                }
                return render(request, "members/add_member.html", context)

            except (ValueError, MemberType.DoesNotExist) as e:
                messages.error(request, f"Invalid member data: {e}")
                return redirect("members:add_member")
        else:
            messages.error(request, "Invalid request.")
            return redirect("members:add_member")

    elif step == "process":
        # Step 3: Final Processing
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            member_data = request.session.get("member_data")
            if not member_data:
                messages.error(request, "Member session expired. Please try again.")
                return redirect("members:add_member")

            try:
                # Get member type
                member_type = get_object_or_404(
                    MemberType, pk=member_data["member_type_id"]
                )

                # Create the member record with specific member_id
                member = Member.objects.create_new_member(
                    first_name=member_data["first_name"],
                    last_name=member_data["last_name"],
                    email=member_data["email"],
                    member_type=member_type,
                    milestone_date=datetime.fromisoformat(
                        member_data["milestone_date"]
                    ).date(),
                    date_joined=datetime.fromisoformat(
                        member_data["date_joined"]
                    ).date(),
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

                # Clear session data
                if "member_data" in request.session:
                    del request.session["member_data"]

                # Create success message
                success_msg = f"Member {member.full_name} (#{member.member_id}) successfully created. Membership expires {member.expiration_date.strftime('%B %d, %Y')}."
                messages.success(request, success_msg)
                return redirect("members:search")

            except Exception as e:
                messages.error(request, f"Error creating member: {e}")
                return redirect("members:add_member")
        else:
            # User cancelled or invalid request
            if "member_data" in request.session:
                del request.session["member_data"]
            messages.info(request, "Member creation cancelled.")
            return redirect("members:add_member")

    else:
        # Invalid step
        return redirect("members:add_member")
