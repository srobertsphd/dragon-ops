from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime, date

from ..models import Member, MemberType
from ..utils import ensure_end_of_month, add_months_to_date
from ..services import MemberService


@staff_member_required
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
def add_member_view(request):
    """Add new member workflow with form, validation, and confirmation"""

    # Get workflow step
    step = request.GET.get("step", "form")

    if step == "form":
        # Step 1: Member Form
        member_types = MemberType.objects.all()

        # Get next available member ID and suggestions using MemberService
        next_member_id, suggested_ids = MemberService.get_suggested_ids(count=5)

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
                # Create member using MemberService
                member = MemberService.create_member(member_data)

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
