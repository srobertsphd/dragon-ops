"""One-page board summary of current members and dues received."""

from decimal import Decimal
from io import BytesIO

from django.db.models import Count, Sum
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from ..models import Member, MemberType, Payment

LEFT = 0.7 * inch
RIGHT_MARGIN = 0.7 * inch
TOP = 0.65 * inch
BOTTOM = 0.55 * inch
PAGE_WIDTH, PAGE_HEIGHT = letter


def _long_date(value):
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _money(amount):
    return f"${amount:,.2f}"


def board_summary_data(start, end, today):
    """Dues received between start and end, grouped by current membership type.

    A member who paid more than once is counted once. Both payments are included
    in the dues total. Every membership type is listed, including those with no
    payments in the range.
    """
    totals = {
        row["member__member_type_id"]: row
        for row in (
            Payment.objects.filter(date__gte=start, date__lte=end)
            .values("member__member_type_id")
            .annotate(
                members=Count("member", distinct=True),
                amount=Sum("amount"),
            )
        )
    }
    rows = []
    for member_type in MemberType.objects.all():
        data = totals.get(member_type.pk, {})
        rows.append(
            {
                "name": member_type.member_type,
                "members": data.get("members") or 0,
                "amount": data.get("amount") or Decimal("0.00"),
            }
        )
    return {
        "report_date": today,
        "start": start,
        "end": end,
        "current_members": Member.objects.filter(status="active").count(),
        "rows": rows,
        "total_members": sum(row["members"] for row in rows),
        "total_amount": sum((row["amount"] for row in rows), Decimal("0.00")),
    }


def generate_board_summary_pdf(summary):
    """Draw the board summary on one US Letter portrait page. Returns PDF bytes."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=0)
    c.setTitle("Board Summary Report")
    width = PAGE_WIDTH - LEFT - RIGHT_MARGIN
    right = LEFT + width

    y = PAGE_HEIGHT - TOP
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-Bold", 14)
    c.drawCentredString(PAGE_WIDTH / 2, y, "The Alano Club of San Jose")
    y -= 26
    c.setFont("Times-Bold", 20)
    c.drawCentredString(PAGE_WIDTH / 2, y, "Board Summary Report")
    y -= 20
    c.setFont("Helvetica", 11)
    c.drawCentredString(PAGE_WIDTH / 2, y, _long_date(summary["report_date"]))
    y -= 14
    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.setLineWidth(0.6)
    c.line(LEFT, y, right, y)

    y -= 26
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 12)
    c.drawString(LEFT, y, "Current members")
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(right, y, f"{summary['current_members']:,}")

    y -= 20
    c.setFont("Helvetica", 11)
    period = f"{_long_date(summary['start'])} through {_long_date(summary['end'])}"
    c.drawString(LEFT, y, period)
    y -= 22

    blocks = [{**row, "total": False} for row in summary["rows"]]
    blocks.append(
        {
            "name": "Total",
            "members": summary["total_members"],
            "amount": summary["total_amount"],
            "total": True,
        }
    )
    available = y - BOTTOM
    stride = min(58, available / len(blocks))
    for block in blocks:
        y = _draw_block(c, y, stride, LEFT, width, right, block)

    c.save()
    buf.seek(0)
    return buf.read()


def _draw_block(c, y, stride, left, width, right, block):
    bar_h = 18 if stride >= 50 else max(14, stride * 0.3)
    if block["total"]:
        c.setFillColorRGB(0.28, 0.28, 0.28)
        label_color = (1, 1, 1)
    else:
        c.setFillColorRGB(0.86, 0.86, 0.86)
        label_color = (0, 0, 0)
    c.rect(left, y - bar_h, width, bar_h, fill=1, stroke=0)
    c.setFillColorRGB(*label_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left + 8, y - bar_h + 5, block["name"].upper())

    body = stride - bar_h
    c.setFillColorRGB(0, 0, 0)
    _detail_line(
        c,
        left,
        right,
        y - bar_h - body * 0.38,
        "Members who paid",
        f"{block['members']:,}",
    )
    _detail_line(
        c,
        left,
        right,
        y - bar_h - body * 0.78,
        "Dues received",
        _money(block["amount"]),
    )
    return y - stride


def _detail_line(c, left, right, baseline, label, value):
    c.setFont("Helvetica", 11)
    c.drawString(left + 12, baseline, label)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(right - 8, baseline, value)
