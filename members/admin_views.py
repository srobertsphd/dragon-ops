from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import Member


@staff_member_required
def deactivate_expired_members_view(request):
    """
    Custom admin view for reviewing and deactivating expired members.

    GET: Display list of eligible members with checkboxes
    POST: Deactivate selected members
    """
    if request.method == "POST":
        # Handle deactivation
        member_uuids = request.POST.getlist("member_uuids")

        if not member_uuids:
            messages.warning(request, "No members selected for deactivation.")
            return redirect("admin:deactivate_expired_members")

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

        return redirect("admin:deactivate_expired_members")

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

    return render(request, "admin/deactivate_expired.html", context)
