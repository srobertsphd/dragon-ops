# Plan: Print Badges report

## Goal

Add a Print Badges report that selects new active members by a date range and produces a PDF laid out for Avery L4787 name-badge sheets (80 × 50 mm, 10 per A4 sheet). Each badge shows first name and last initial, the club name, the member ID as the badge number, and the date the member joined as Since.

The visual reference is `docs/Badges.pdf`. That file is the style to match (wording, relative type sizes, centering). The physical placement follows the Avery L4787 sheet, so text lands inside the white area of each badge.

## Phases

- [x] **1. Badge content.** Turn a member into badge text: `Jose M.`, member ID, and `date_joined` as Since. Tests only. No page and no PDF.
- [x] **2. PDF layout.** Draw those lines on the Avery L4787 grid in `members/reports/badges.py`. A4, 10 per page, centered, shrink-to-fit.
- [x] **3. Report page.** Print Badges card, date form (last 30 days through today), preview, and PDF download.
- [ ] **4. Print check.** Print one page at 100% on plain A4 and hold it against an Avery L4787 sheet.

## What the user sees

On the Reports page, in the same blue view/print group as Print Address Labels, add a card:

- Title: Print Badges
- Short text: printable name badges for new members, Avery L4787 (80 × 50 mm, 10 per sheet)
- Button opens the badge report

The badge report page has two date fields:

- Start date defaults to 30 days before today
- End date defaults to today (the day the page is opened)
- Both can be changed
- End date cannot be before the start date
- End date cannot be after today

Preview shows the PDF itself, one full page at a time, in the page. That is the same file that prints. A Generate PDF button downloads it. If nobody joined in that range, show a message and do not offer a PDF.

Printing is from that PDF. The user loads Avery L4787 sheets and prints at actual size (100%, A4, no "fit to page").

## Who gets a badge

Same idea as New Member Export: active members whose join date falls in the range, inclusive.

- Status is active
- `date_joined` is on or after the start date and on or before the end date
- `member_id` is set (active members have one; skip anyone who does not)

`date_joined` is the club membership start. That is the Since date. There is no separate "active since" field. The existing Available Badge Numbers report already treats `member_id` as the badge number.

Order: `date_joined`, then last name, then first name. Ten badges per page; extra members continue on the next page. No blank badges are reserved, and there is no "skip used labels" control.

Unlike New Member Export, do not cap the start date at six months. A later reprint of an older batch should still work.

## What prints on each badge

Match `docs/Badges.pdf`:

1. `The Alano Club of San Jose` — centered, smaller
2. First name, space, last initial, period — centered, largest. Example: `Jose M.`
3. One bottom line: `Badge No.` then the member ID, then `Since:` then the join date

Do not print the full last name.

Name rules:

- Last initial is the first character of `last_name`, uppercased, with a period
- If `last_name` is empty, print the first name only
- Member ID is the integer as stored (`24`, not `024`)
- Since date format matches the sample: `5/2/2026` (no leading zeros)

## Fit and centering

Every line is centered in the printable window of that badge.

The L4787 badge has a blue border. Text stays inside the white area. Use the glabels L4785/L4787 waste inset as the safe padding: 7.5 mm on the left and right, 2.5 mm on the top and bottom. That leaves about 65 × 45 mm for type.

If a line is wider than that window, reduce that line's font size until it fits, then center it. Do this per badge so a short name stays large and a long name (`Valentino D.`) still fits. The club name and the member name are centered. The bottom line is one row: `Badge No.` and the ID on the left, `Since:` and the date on the right, both kept inside the window.

Starting sizes, taken from `docs/Badges.pdf`:

- Club line: Times-Bold, 16 pt, black
- Name: Times-Bold, 30 pt, black, shrink if needed
- Bottom line, 12 pt: `Badge No.` and `Since:` in Helvetica-Bold burgundy (`rgb(0.5, 0, 0)`); the ID and the date in Times-Bold black

The sample embeds Times New Roman and Arial. ReportLab's built-in Times and Helvetica are the stand-in, same approach as the address-label PDF. Do not add font files.

## Avery sheet

L4787 is the same layout as Avery L4785 (glabels template). Page size is A4, not US Letter.

| Setting | Value |
| --- | --- |
| Page | A4 (210 × 297 mm) |
| Badge | 80 × 50 mm |
| Grid | 2 columns × 5 rows |
| Left origin | 18 mm |
| Top origin | 13 mm |
| Horizontal pitch | 95 mm (15 mm gap) |
| Vertical pitch | 55 mm (5 mm gap) |
| Corner radius | 4 mm (do not draw it; the sticker already has it) |

`docs/Badges.pdf` is US Letter because it was printed through a Windows driver. Copy its wording and type sizes, not its page size or absolute coordinates. An A4 PDF printed at 100% is what lines up with these sheets.

On the report page, say: print on A4, scale 100%, and do a plain-paper test held up to a badge sheet before using the stickers.

## How it fits the app

Follow Print Address Labels: a staff-only view, a form, a preview, then a ReportLab PDF built the same way as `members/reports/address_labels.py`.

Reuse the new-member filter from `new_member_export_view` (`status="active"`, `date_joined` between the two dates). Staff login stays as it is (`staff_member_required`).

## Files to add or change

| File | Change |
| --- | --- |
| `members/reports/badges.py` | New. Layout constants and PDF generation. |
| `members/templates/members/reports/badges.html` | New. Date form, preview grid, generate button. |
| `members/templates/members/reports/landing.html` | One card in the blue section. |
| `members/views/reports.py` | New view: defaults, validation, preview, PDF. |
| `members/views/__init__.py` | Export the view. |
| `members/urls.py` | `reports/badges/` named `badges`. |
| `tests/test_badge_report.py` | New. Filter, name format, PDF basics. |

Rough size: about 120 lines in the PDF module, about 80 in the view, about 100 in the template, about 20 on the landing page and URL wiring, and a focused test file. No model or migration changes.

## Tests

- Default start date is 30 days before today, and the default end date is today
- End date before start date is rejected
- End date after today is rejected
- Only active members with `date_joined` in range and a `member_id` are included
- Badge text is `First L.` and never the full last name
- Since date is `date_joined`
- Badge number is `member_id`
- Empty range does not return a PDF
- Generated PDF is A4 and uses a new page after every 10 badges

## Out of scope

- Reprinting one member from the member edit page
- Skipping already-used positions on a partial sheet
- Logos, color, or a drawn border
- Changing how member IDs are assigned
