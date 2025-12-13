from django.shortcuts import render, redirect
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from datetime import date, timedelta

from ..models import Member, Payment


@login_required
def reports_landing_view(request):
    """Reports landing page with links to available reports"""
    return render(request, "members/reports/landing.html")


@login_required
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
        from ..reports.pdf import generate_members_pdf

        return generate_members_pdf(request, context)

    # Otherwise return HTML version for preview
    return render(request, "members/reports/current_members.html", context)


@login_required
def recent_payments_report_view(request):
    """Recent payments report (last year) with CSV export"""
    one_year_ago = date.today() - timedelta(days=365)

    payments = (
        Payment.objects.filter(date__gte=one_year_ago)
        .select_related("member", "payment_method")
        .order_by("-date")
    )

    if request.GET.get("format") == "csv":
        from ..reports.csv import generate_payments_csv

        return generate_payments_csv(payments)

    context = {
        "payments": payments,
        "report_date": date.today(),
        "start_date": one_year_ago,
    }
    return render(request, "members/reports/recent_payments.html", context)


@login_required
def newsletter_export_view(request):
    """Generate Excel export of active members for newsletter distribution"""
    active_members = Member.objects.filter(status="active").order_by("member_id")

    from ..reports.excel import generate_newsletter_excel

    return generate_newsletter_excel(active_members)


@login_required
def new_member_export_view(request):
    """
    Generate Excel export of new members (active members who joined within date range).

    GET: Display date range selection form
    POST: Validate dates and generate Excel export
    """
    today = date.today()
    min_date = today - timedelta(days=180)  # 6 months ago

    if request.method == "POST":
        # Get form data
        start_date_str = request.POST.get("start_date")
        end_date_str = request.POST.get("end_date")

        form_errors = {}
        validation_errors = []

        # Validate dates are provided
        if not start_date_str:
            form_errors["start_date"] = "Start date is required."
        if not end_date_str:
            form_errors["end_date"] = "End date is required."

        if form_errors:
            context = {
                "today": today,
                "min_date": min_date,
                "form_errors": form_errors,
                "start_date": start_date_str or "",
                "end_date": end_date_str or "",
            }
            return render(request, "members/reports/new_member_export.html", context)

        # Parse dates
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            form_errors["start_date"] = "Invalid date format."
            context = {
                "today": today,
                "min_date": min_date,
                "form_errors": form_errors,
                "start_date": start_date_str,
                "end_date": end_date_str,
            }
            return render(request, "members/reports/new_member_export.html", context)

        # Server-side validation
        # Check start date is not more than 6 months ago
        if start_date < min_date:
            validation_errors.append("Start date cannot be more than 6 months ago.")
            form_errors["start_date"] = "Start date cannot be more than 6 months ago."

        # Check end date is not in the future
        if end_date > today:
            validation_errors.append("End date cannot exceed today.")
            form_errors["end_date"] = "End date cannot exceed today."

        # Check end date is not before start date
        if end_date < start_date:
            validation_errors.append("End date must be on or after start date.")
            form_errors["end_date"] = "End date must be on or after start date."

        # If validation errors, return form with errors
        if form_errors or validation_errors:
            context = {
                "today": today,
                "min_date": min_date,
                "form_errors": form_errors,
                "start_date": start_date_str,
                "end_date": end_date_str,
            }
            if validation_errors:
                messages.error(request, " ".join(validation_errors))
            return render(request, "members/reports/new_member_export.html", context)

        # Validation passed - filter members and generate Excel
        # Filter active members where date_joined is within range
        new_members = Member.objects.filter(
            status="active",
            date_joined__gte=start_date,
            date_joined__lte=end_date,
        ).order_by("member_id")

        # Import and call Excel generation function
        from ..reports.excel import generate_new_member_excel

        return generate_new_member_excel(new_members)

    # GET request - display form
    context = {
        "today": today,
        "min_date": min_date,
        "start_date": "",
        "end_date": "",
    }
    return render(request, "members/reports/new_member_export.html", context)


def milestone_falls_in_range(milestone_date, start_date, end_date, current_year=None):
    """
    Check if milestone date (month/day) falls within selected range THIS YEAR.

    Args:
        milestone_date: Original milestone date (can be any year)
        start_date: Start date of the range
        end_date: End date of the range
        current_year: Year to use for milestone date (defaults to today's year)

    Returns:
        bool: True if milestone date (this year) falls within range, False otherwise
    """
    if current_year is None:
        current_year = date.today().year

    # Extract month and day from milestone_date
    milestone_month = milestone_date.month
    milestone_day = milestone_date.day

    # Handle leap year dates (Feb 29) - use Feb 28 in non-leap years
    try:
        milestone_this_year = date(current_year, milestone_month, milestone_day)
    except ValueError:
        # Leap year date in non-leap year - use Feb 28
        milestone_this_year = date(current_year, 2, 28)

    # Check if milestone date (this year) falls within selected range
    return start_date <= milestone_this_year <= end_date


@login_required
def milestone_export_view(request):
    """
    Generate Excel export of active members whose milestone dates fall within date range.

    GET: Display date range selection form
    POST: Validate dates and generate Excel export
    """
    today = date.today()
    min_date = today - timedelta(days=180)  # 6 months ago
    max_date = today + timedelta(days=180)  # 6 months from today
    end_date_default = today + timedelta(days=30)  # Default: 30 days from today

    if request.method == "POST":
        # Get form data
        start_date_str = request.POST.get("start_date")
        end_date_str = request.POST.get("end_date")

        form_errors = {}
        validation_errors = []

        # Validate dates are provided
        if not start_date_str:
            form_errors["start_date"] = "Start date is required."
        if not end_date_str:
            form_errors["end_date"] = "End date is required."

        if form_errors:
            context = {
                "today": today,
                "min_date": min_date,
                "max_date": max_date,
                "end_date_default": end_date_default,
                "form_errors": form_errors,
                "start_date": start_date_str or "",
                "end_date": end_date_str or "",
            }
            return render(request, "members/reports/milestone_export.html", context)

        # Parse dates
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            form_errors["start_date"] = "Invalid date format."
            context = {
                "today": today,
                "min_date": min_date,
                "max_date": max_date,
                "end_date_default": end_date_default,
                "form_errors": form_errors,
                "start_date": start_date_str,
                "end_date": end_date_str,
            }
            return render(request, "members/reports/milestone_export.html", context)

        # Server-side validation
        # Check start date is not more than 6 months ago
        if start_date < min_date:
            validation_errors.append("Start date cannot be more than 6 months ago.")
            form_errors["start_date"] = "Start date cannot be more than 6 months ago."

        # Check start date is not more than 6 months in the future
        if start_date > max_date:
            validation_errors.append(
                "Start date cannot be more than 6 months in the future."
            )
            form_errors["start_date"] = (
                "Start date cannot be more than 6 months in the future."
            )

        # Check end date is not more than 6 months ago
        if end_date < min_date:
            validation_errors.append("End date cannot be more than 6 months ago.")
            form_errors["end_date"] = "End date cannot be more than 6 months ago."

        # Check end date is not more than 6 months in the future
        if end_date > max_date:
            validation_errors.append(
                "End date cannot be more than 6 months in the future."
            )
            form_errors["end_date"] = (
                "End date cannot be more than 6 months in the future."
            )

        # Check end date is not before start date
        if end_date < start_date:
            validation_errors.append("End date must be on or after start date.")
            form_errors["end_date"] = "End date must be on or after start date."

        # If validation errors, return form with errors
        if form_errors or validation_errors:
            context = {
                "today": today,
                "min_date": min_date,
                "max_date": max_date,
                "end_date_default": end_date_default,
                "form_errors": form_errors,
                "start_date": start_date_str,
                "end_date": end_date_str,
            }
            if validation_errors:
                messages.error(request, " ".join(validation_errors))
            return render(request, "members/reports/milestone_export.html", context)

        # Validation passed - filter members by milestone dates falling in range THIS YEAR
        # Get all active members with milestone dates
        active_members_with_milestones = Member.objects.filter(
            status="active",
            milestone_date__isnull=False,
        )

        # Filter members whose milestone date (this year) falls within selected range
        current_year = today.year
        filtered_members = [
            member
            for member in active_members_with_milestones
            if milestone_falls_in_range(
                member.milestone_date, start_date, end_date, current_year
            )
        ]

        # Order by member_id
        filtered_members.sort(key=lambda m: m.member_id or 0)

        # Import and call Excel generation function
        from ..reports.excel import generate_milestone_excel

        return generate_milestone_excel(filtered_members)

    # GET request - display form
    context = {
        "today": today,
        "min_date": min_date,
        "max_date": max_date,
        "end_date_default": end_date_default,
        "start_date": "",
        "end_date": "",
    }
    return render(request, "members/reports/milestone_export.html", context)


@staff_member_required
def deactivate_expired_members_report_view(request):
    """
    Reports view for reviewing and deactivating expired members.

    GET: Display list of eligible members with checkboxes
    POST: Deactivate selected members
    """
    if request.method == "POST":
        # Handle deactivation
        member_uuids = request.POST.getlist("member_uuids")

        if not member_uuids:
            messages.warning(request, "No members selected for deactivation.")
            return redirect("members:deactivate_expired_members")

        # Get members and validate they're still eligible
        members = Member.objects.filter(member_uuid__in=member_uuids, status="active")

        deactivated_count = 0
        errors = []

        with transaction.atomic():
            for member in members:
                try:
                    # Double-check eligibility before deactivating
                    if member.is_expired_for_deactivation():
                        # Check for payments after expiration
                        has_payment_after = member.payments.filter(
                            date__gt=member.expiration_date
                        ).exists()

                        if not has_payment_after:
                            member.deactivate()
                            deactivated_count += 1
                        else:
                            errors.append(
                                f"{member.full_name} has a payment after expiration"
                            )
                    else:
                        errors.append(f"{member.full_name} is not expired 90+ days")
                except Exception as e:
                    errors.append(f"Error deactivating {member.full_name}: {str(e)}")

        if deactivated_count > 0:
            messages.success(
                request, f"Successfully deactivated {deactivated_count} member(s)."
            )

        if errors:
            for error in errors:
                messages.error(request, error)

        return redirect("members:deactivate_expired_members")

    # GET request - display list
    eligible_members = Member.objects.get_expired_without_payment()

    # Calculate days expired for each member
    members_with_info = []
    for member in eligible_members:
        members_with_info.append(
            {
                "member": member,
                "days_expired": member.days_expired(),
                "last_payment_date": member.last_payment_date,
            }
        )

    # Sort by days expired (most expired first)
    members_with_info.sort(key=lambda x: x["days_expired"], reverse=True)

    context = {
        "members": members_with_info,
        "total_count": len(members_with_info),
        "title": "Deactivate Expired Members",
    }

    return render(request, "members/reports/deactivate_expired.html", context)
