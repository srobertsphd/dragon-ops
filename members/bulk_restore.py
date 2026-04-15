"""
Bulk-load a Django dumpdata JSON fixture into the database using bulk_create.

Django's loaddata does one INSERT per object. Over a remote connection (Supabase),
~1.5s latency per round trip makes it unusable for 2000+ objects. bulk_create
batches them into a few large INSERTs and finishes in seconds.
"""

import json
import uuid
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection

from members.models import Member, MemberType, Payment, PaymentMethod


def _parse_date(val):
    if not val:
        return None
    return date.fromisoformat(val) if len(val) == 10 else datetime.fromisoformat(val).date()


def _parse_datetime(val):
    if not val:
        return None
    return datetime.fromisoformat(val)


def bulk_load_from_json(filepath, log=None):
    """Load a dumpdata JSON fixture using bulk operations.

    Args:
        filepath: Path to the JSON fixture file.
        log: Callable for status messages (e.g. self.stdout.write). Optional.
    """
    def out(msg):
        if log:
            log(msg)

    with open(filepath) as f:
        data = json.load(f)

    by_model = defaultdict(list)
    for item in data:
        by_model[item["model"]].append(item)

    out(f"  Loaded {len(data)} objects from {filepath}")

    # MemberType
    objs = [
        MemberType(id=item["pk"], **item["fields"])
        for item in by_model["members.membertype"]
    ]
    if objs:
        MemberType.objects.bulk_create(objs, batch_size=200)
        out(f"  MemberTypes: {len(objs)}")

    # PaymentMethod
    objs = [
        PaymentMethod(id=item["pk"], **item["fields"])
        for item in by_model["members.paymentmethod"]
    ]
    if objs:
        PaymentMethod.objects.bulk_create(objs, batch_size=200)
        out(f"  PaymentMethods: {len(objs)}")

    # Users (individual saves to preserve hashed passwords and M2M handling)
    for item in by_model["auth.user"]:
        f = item["fields"]
        u = User(
            password=f["password"],
            is_superuser=f["is_superuser"],
            username=f["username"],
            first_name=f.get("first_name", ""),
            last_name=f.get("last_name", ""),
            email=f.get("email", ""),
            is_staff=f["is_staff"],
            is_active=f["is_active"],
            date_joined=datetime.fromisoformat(f["date_joined"]),
        )
        if f.get("last_login"):
            u.last_login = datetime.fromisoformat(f["last_login"])
        u.save()
    user_count = len(by_model["auth.user"])
    if user_count:
        out(f"  Users: {user_count}")

    # Members
    objs = []
    for item in by_model["members.member"]:
        f = item["fields"]
        objs.append(Member(
            member_uuid=uuid.UUID(item["pk"]),
            member_id=f["member_id"],
            preferred_member_id=f.get("preferred_member_id"),
            first_name=f["first_name"],
            last_name=f["last_name"],
            email=f.get("email", ""),
            member_type_id=f["member_type"],
            status=f["status"],
            expiration_date=_parse_date(f.get("expiration_date")),
            milestone_date=_parse_date(f.get("milestone_date")),
            date_joined=_parse_date(f.get("date_joined")),
            date_inactivated=_parse_date(f.get("date_inactivated")),
            home_address=f.get("home_address", ""),
            home_city=f.get("home_city", ""),
            home_state=f.get("home_state", ""),
            home_zip=f.get("home_zip", ""),
            home_phone=f.get("home_phone", ""),
            created_at=_parse_datetime(f.get("created_at")),
            updated_at=_parse_datetime(f.get("updated_at")),
        ))
    if objs:
        Member.objects.bulk_create(objs, batch_size=200)
        out(f"  Members: {len(objs)}")

    # Payments
    objs = []
    for item in by_model["members.payment"]:
        f = item["fields"]
        objs.append(Payment(
            id=item["pk"],
            member_id=uuid.UUID(f["member"]),
            payment_method_id=f["payment_method"],
            amount=Decimal(str(f["amount"])),
            date=_parse_date(f["date"]),
            receipt_number=f.get("receipt_number", ""),
            new_expiration_date=_parse_date(f.get("new_expiration_date")),
            created_at=_parse_datetime(f.get("created_at")),
            updated_at=_parse_datetime(f.get("updated_at")),
        ))
    if objs:
        Payment.objects.bulk_create(objs, batch_size=200)
        out(f"  Payments: {len(objs)}")

    # Reset payment sequence
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT setval(
                'members_payment_id_seq',
                COALESCE((SELECT MAX(id) FROM members_payment), 1),
                true
            )
        """)
    out("  Sequences reset.")
