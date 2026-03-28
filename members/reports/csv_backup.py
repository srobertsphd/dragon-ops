"""
CSV backup export: schema definition and CSV/ZIP generation.

Schema is the single source of truth for the schema page and schema file download.
"""

import csv
import io
import json
import zipfile
from datetime import datetime

from members.models import Member, MemberType, Payment, PaymentMethod

# Export schema: list of table definitions for the four CSV files.
# Each item: dict with "table", "filename", "columns".
# "columns": list of (column_name, description) for display/schema file.
CSV_EXPORT_SCHEMA = [
    {
        "table": "member_types",
        "filename": "member_types.csv",
        "columns": [
            ("id", "Primary key"),
            ("member_type", "Type name"),
            ("member_dues", "Dues amount"),
            ("num_months", "Duration in months"),
        ],
    },
    {
        "table": "payment_methods",
        "filename": "payment_methods.csv",
        "columns": [
            ("id", "Primary key"),
            ("payment_method", "Payment method name"),
        ],
    },
    {
        "table": "members",
        "filename": "members.csv",
        "columns": [
            ("member_uuid", "Member UUID (permanent key)"),
            ("member_id", "Member ID (1-1000, recyclable)"),
            ("preferred_member_id", "Preferred ID for reactivation"),
            ("first_name", "First name"),
            ("last_name", "Last name"),
            ("email", "Email"),
            ("member_type_id", "Foreign key to member_types"),
            ("member_type", "Joined: type name"),
            ("member_dues", "Joined: dues amount"),
            ("num_months", "Joined: duration in months"),
            ("status", "active | inactive | deceased"),
            ("expiration_date", "Membership expiration"),
            ("milestone_date", "Sobriety/milestone date"),
            ("date_joined", "Club join date"),
            ("date_inactivated", "Inactivation date if applicable"),
            ("home_address", "Street address"),
            ("home_city", "City"),
            ("home_state", "State code"),
            ("home_zip", "ZIP"),
            ("home_phone", "Phone"),
            ("created_at", "Record created"),
            ("updated_at", "Record updated"),
        ],
    },
    {
        "table": "payments",
        "filename": "payments.csv",
        "columns": [
            ("id", "Primary key"),
            ("member_uuid", "From member (link to members.csv)"),
            ("member_id", "From member (display)"),
            ("member_last_name", "From member"),
            ("member_first_name", "From member"),
            ("payment_method_id", "Foreign key to payment_methods"),
            ("payment_method", "Joined: payment method name"),
            ("amount", "Payment amount"),
            ("date", "Payment date"),
            ("receipt_number", "Receipt number"),
            ("created_at", "Record created"),
            ("updated_at", "Record updated"),
        ],
    },
]


def get_export_schema():
    """Return the export schema for use in views and schema download."""
    return CSV_EXPORT_SCHEMA


def _csv_value(val):
    """Format a value for CSV (None -> empty string, date/datetime -> YYYY-MM-DD)."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.date().isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def generate_member_types_csv(queryset=None) -> str:
    """Return CSV content for member_types. Uses all MemberType rows if queryset not provided."""
    if queryset is None:
        queryset = MemberType.objects.all()
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow([c[0] for c in CSV_EXPORT_SCHEMA[0]["columns"]])
    for row in queryset:
        writer.writerow([
            _csv_value(row.id),
            _csv_value(row.member_type),
            _csv_value(row.member_dues),
            _csv_value(row.num_months),
        ])
    return out.getvalue()


def generate_payment_methods_csv(queryset=None) -> str:
    """Return CSV content for payment_methods. Uses all PaymentMethod rows if queryset not provided."""
    if queryset is None:
        queryset = PaymentMethod.objects.all()
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow([c[0] for c in CSV_EXPORT_SCHEMA[1]["columns"]])
    for row in queryset:
        writer.writerow([
            _csv_value(row.id),
            _csv_value(row.payment_method),
        ])
    return out.getvalue()


def generate_members_csv(queryset=None) -> str:
    """Return CSV content for members with joined MemberType. Uses all Member rows if queryset not provided."""
    if queryset is None:
        queryset = Member.objects.select_related("member_type").all()
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow([c[0] for c in CSV_EXPORT_SCHEMA[2]["columns"]])
    for m in queryset:
        mt = m.member_type
        writer.writerow([
            _csv_value(m.member_uuid),
            _csv_value(m.member_id),
            _csv_value(m.preferred_member_id),
            _csv_value(m.first_name),
            _csv_value(m.last_name),
            _csv_value(m.email),
            _csv_value(m.member_type_id),
            _csv_value(mt.member_type if mt else None),
            _csv_value(mt.member_dues if mt else None),
            _csv_value(mt.num_months if mt else None),
            _csv_value(m.status),
            _csv_value(m.expiration_date),
            _csv_value(m.milestone_date),
            _csv_value(m.date_joined),
            _csv_value(m.date_inactivated),
            _csv_value(m.home_address),
            _csv_value(m.home_city),
            _csv_value(m.home_state),
            _csv_value(m.home_zip),
            _csv_value(m.home_phone),
            _csv_value(m.created_at),
            _csv_value(m.updated_at),
        ])
    return out.getvalue()


def generate_payments_csv_backup(queryset=None) -> str:
    """Return CSV content for payments with joined member and payment_method. Uses all Payment rows if queryset not provided."""
    if queryset is None:
        queryset = Payment.objects.select_related("member", "payment_method").all()
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow([c[0] for c in CSV_EXPORT_SCHEMA[3]["columns"]])
    for p in queryset:
        writer.writerow([
            _csv_value(p.id),
            _csv_value(p.member_id),
            _csv_value(p.member.member_id),
            _csv_value(p.member.last_name),
            _csv_value(p.member.first_name),
            _csv_value(p.payment_method_id),
            _csv_value(
                p.payment_method.payment_method if p.payment_method else None
            ),
            _csv_value(p.amount),
            _csv_value(p.date),
            _csv_value(p.receipt_number),
            _csv_value(p.created_at),
            _csv_value(p.updated_at),
        ])
    return out.getvalue()


def build_csv_backup_zip():
    """
    Build a ZIP containing the four CSV files and the schema JSON. Returns ZIP bytes.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            CSV_EXPORT_SCHEMA[0]["filename"],
            generate_member_types_csv(),
        )
        zf.writestr(
            CSV_EXPORT_SCHEMA[1]["filename"],
            generate_payment_methods_csv(),
        )
        zf.writestr(
            CSV_EXPORT_SCHEMA[2]["filename"],
            generate_members_csv(),
        )
        zf.writestr(
            CSV_EXPORT_SCHEMA[3]["filename"],
            generate_payments_csv_backup(),
        )
        zf.writestr(
            "csv_export_schema.json",
            json.dumps(get_export_schema(), indent=2),
        )
    buf.seek(0)
    return buf.getvalue()
