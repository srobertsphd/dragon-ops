from io import BytesIO

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Avery 5160 / U-line S-5042 layout (US Letter, 30 labels per sheet)
LABEL_WIDTH = 2.625 * inch
LABEL_HEIGHT = 1.0 * inch
TOP_MARGIN = 0.5 * inch
SIDE_MARGIN = 0.1875 * inch
H_PITCH = 2.75 * inch  # horizontal center-to-center
COLS = 3
ROWS = 10

# Text positioning within each label
FONT_NAME = "Helvetica"
FONT_SIZE = 10
LEFT_PAD = 0.18 * inch
LINE_HEIGHT = FONT_SIZE + 2  # points
NUM_LINES = 3


def _label_origin(col, row):
    """Return (x, y) of the top-left corner of a label cell."""
    page_width, page_height = letter
    x = SIDE_MARGIN + col * H_PITCH
    y = page_height - TOP_MARGIN - row * LABEL_HEIGHT
    return x, y


def generate_address_labels_pdf(members, month_name, year):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    label_index = 0
    for member in members:
        col = label_index % COLS
        row = (label_index // COLS) % ROWS

        if label_index > 0 and col == 0 and row == 0:
            c.showPage()

        x, y = _label_origin(col, row)
        tx = x + LEFT_PAD
        text_block_height = NUM_LINES * LINE_HEIGHT
        ty = y - (LABEL_HEIGHT - text_block_height) / 2 - FONT_SIZE

        c.setFont(FONT_NAME, FONT_SIZE)

        # Line 1: Last, First    MM/DD/YYYY
        ms = member.milestone_date.strftime("%-m/%-d/%Y") if member.milestone_date else ""
        line1 = f"{member.last_name}, {member.first_name}    {ms}"
        c.drawString(tx, ty, line1)

        # Line 2: Street address
        ty -= LINE_HEIGHT
        c.drawString(tx, ty, member.home_address.strip())

        # Line 3: City, ST ZIP
        ty -= LINE_HEIGHT
        parts = []
        if member.home_city:
            parts.append(member.home_city.strip())
        if member.home_state:
            if parts:
                parts[-1] += ","
            parts.append(member.home_state.strip())
        if member.home_zip:
            parts.append(member.home_zip.strip())
        c.drawString(tx, ty, " ".join(parts))

        label_index += 1

    c.save()
    buf.seek(0)

    filename = f"address_labels_{month_name}_{year}.pdf"
    response = HttpResponse(buf.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
