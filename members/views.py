from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime

from .models import Member, Payment


def landing_view(request):
    """Landing page with system overview"""
    return render(request, "members/landing.html")


def search_view(request):
    """Simple member search page"""
    query = request.GET.get("q", "").strip()
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

    # Perform search if query provided
    if query:
        # Try to search by member ID first
        try:
            member_id = int(query)
            members = Member.objects.filter(member_id=member_id).select_related(
                "member_type"
            )
        except ValueError:
            # Search by name
            members = (
                Member.objects.filter(
                    Q(first_name__icontains=query) | Q(last_name__icontains=query)
                )
                .select_related("member_type")
                .order_by("last_name", "first_name")
            )

    context = {
        "query": query,
        "members": members,
        "active_members_count": active_members_count,
        "total_payments_count": total_payments_count,
        "available_ids_count": available_ids_count,
    }

    return render(request, "members/search.html", context)


def member_detail_view(request, member_uuid):
    """Display detailed member information and payment history"""
    member = get_object_or_404(
        Member.objects.select_related("member_type"), member_uuid=member_uuid
    )

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
