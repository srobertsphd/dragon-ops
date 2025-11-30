from django.http import HttpResponse
import csv
from datetime import date


def generate_payments_csv(payments_queryset):
    """Generate CSV export of recent payments"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="recent_payments_{date.today().strftime("%Y_%m_%d")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Date",
            "Last Name",
            "First Name",
            "Member ID",
            "Payment Amount",
            "Receipt Number",
        ]
    )

    for payment in payments_queryset:
        writer.writerow(
            [
                payment.date.strftime("%Y-%m-%d"),
                payment.member.last_name,
                payment.member.first_name,
                payment.member.member_id or "",
                str(payment.amount),
                payment.receipt_number or "",
            ]
        )

    return response
