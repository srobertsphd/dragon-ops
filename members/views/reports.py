from django.shortcuts import render
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required
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
