from django.shortcuts import render
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required

from ..models import Member, Payment


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
