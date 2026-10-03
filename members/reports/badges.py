from io import BytesIO

from reportlab.lib.colors import Color, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

CLUB_NAME = "The Alano Club of San Jose"

# Avery L4787 / L4785: 80×50 mm, 2×5 on A4. Padding keeps type inside the blue border.
LABEL_W = 80 * mm
LABEL_H = 50 * mm
ORIGIN_X = 18 * mm
ORIGIN_TOP = 13 * mm
PITCH_X = 95 * mm
PITCH_Y = 55 * mm
PAD_X = 7.5 * mm
PAD_Y = 2.5 * mm
COLS = 2
ROWS = 5
PER_PAGE = COLS * ROWS

# Sizes and colors taken from docs/Badges.pdf. Burgundy is the sample's 0.5 0 0.
BURGUNDY = Color(0.5, 0, 0)
CLUB_FONT = "Times-Bold"
CLUB_SIZE = 16
NAME_FONT = "Times-Bold"
NAME_SIZE = 30
LABEL_FONT = "Helvetica-Bold"
VALUE_FONT = "Times-Bold"
META_SIZE = 12
MIN_FONT_SIZE = 6


def badge_display_name(first_name, last_name):
    """First name and last initial. Full last name is never printed."""
    first = first_name.strip()
    last = last_name.strip()
    if not last:
        return first
    return f"{first} {last[0].upper()}."


def format_since_date(date_joined):
    """Join date as M/D/YYYY, matching the sample badges."""
    return f"{date_joined.month}/{date_joined.day}/{date_joined.year}"


def badge_content(first_name, last_name, member_id, date_joined):
    """Text lines for one badge."""
    return {
        "club": CLUB_NAME,
        "name": badge_display_name(first_name, last_name),
        "badge_no": str(member_id),
        "since": format_since_date(date_joined),
    }


def fitted_font_size(text, font_name, max_size, max_width, min_size=MIN_FONT_SIZE):
    """Largest size at or below max_size that keeps text inside max_width."""
    size = max_size
    while size > min_size and stringWidth(text, font_name, size) > max_width:
        size -= 0.5
    return size


def _draw_text(c, text, font, size, x, y, fill):
    """Same fill-and-stroke weight on every card. Render mode is set each time so it cannot leak."""
    c.setStrokeColor(fill)
    c.setFillColor(fill)
    c.setLineWidth(0.6)
    text_obj = c.beginText(x, y)
    text_obj.setTextRenderMode(2)
    text_obj.setFont(font, size)
    text_obj.setFillColor(fill)
    text_obj.setStrokeColor(fill)
    text_obj.textOut(text)
    c.drawText(text_obj)


def _draw_centered(c, text, font_name, max_size, center_x, baseline, max_width):
    size = fitted_font_size(text, font_name, max_size, max_width)
    width = stringWidth(text, font_name, size)
    _draw_text(c, text, font_name, size, center_x - width / 2, baseline, black)


def _pair_width(label, value, size):
    return stringWidth(label + " ", LABEL_FONT, size) + stringWidth(value, VALUE_FONT, size)


def _meta_font_size(badge_no, since, max_width):
    """Shrink until both bottom pairs fit, with a gap between them."""
    size = META_SIZE
    min_gap = 10
    while size > MIN_FONT_SIZE:
        used = (
            _pair_width("Badge No.", badge_no, size)
            + _pair_width("Since:", since, size)
            + min_gap
        )
        if used <= max_width:
            return size
        size -= 0.5
    return size


def _draw_badge(c, col, row, member):
    content = badge_content(
        member.first_name, member.last_name, member.member_id, member.date_joined
    )
    _, page_h = A4
    x = ORIGIN_X + col * PITCH_X
    top = page_h - ORIGIN_TOP - row * PITCH_Y
    bottom = top - LABEL_H

    window_bottom = bottom + PAD_Y
    window_height = LABEL_H - 2 * PAD_Y
    window_width = LABEL_W - 2 * PAD_X
    center_x = x + LABEL_W / 2

    window_left = x + PAD_X
    baseline_club = window_bottom + window_height * 0.82
    baseline_name = window_bottom + window_height * 0.42
    baseline_meta = window_bottom + window_height * 0.08

    _draw_centered(
        c, content["club"], CLUB_FONT, CLUB_SIZE, center_x, baseline_club, window_width
    )
    _draw_centered(
        c, content["name"], NAME_FONT, NAME_SIZE, center_x, baseline_name, window_width
    )

    size = _meta_font_size(content["badge_no"], content["since"], window_width)
    label = "Badge No."
    _draw_text(c, label, LABEL_FONT, size, window_left, baseline_meta, BURGUNDY)
    number_x = window_left + stringWidth(label + " ", LABEL_FONT, size)
    _draw_text(c, content["badge_no"], VALUE_FONT, size, number_x, baseline_meta, black)

    since = "Since:"
    date_w = stringWidth(content["since"], VALUE_FONT, size)
    since_w = stringWidth(since + " ", LABEL_FONT, size)
    right = window_left + window_width
    _draw_text(c, since, LABEL_FONT, size, right - date_w - since_w, baseline_meta, BURGUNDY)
    _draw_text(c, content["since"], VALUE_FONT, size, right - date_w, baseline_meta, black)


def generate_badges_pdf(members):
    """A4 PDF of name badges, 10 per page, for Avery L4787."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=0)
    for index, member in enumerate(members):
        if index > 0 and index % PER_PAGE == 0:
            c.showPage()
        slot = index % PER_PAGE
        _draw_badge(c, slot % COLS, slot // COLS, member)
    c.save()
    return buf.getvalue()
