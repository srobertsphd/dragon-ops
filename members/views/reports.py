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
