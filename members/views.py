from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime

from .models import Member, Payment


def landing_view(request):
    """Landing page with system overview"""
    return render(request, "members/landing.html")


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
