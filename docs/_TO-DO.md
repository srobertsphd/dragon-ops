March 28, 2026. Things left to do for Tony.

1. Create member reports with three past payments.
2. Create a mechanism for people to pause their membership
3. Add a checkbox on the payment page that includes monthly, six months, and thirteen month dues.
    a. This will require that the member type table gets updated with these amounts or a formula.
4. Add functionality in the payment page that indicates the previous expiration date for each payment listed under the member. It should have an expiration date next to it. Maybe that's only in the payment history, or on that member page. Maybe that actually goes into the payment functionality.
5. Add functionality that tells if the receipt number was already used for a different or same payment.  ie: filter for double entries etc.  

######################################################################

## Item 4 Implementation Plan: Payment Expiration Tracking
**Goal:** Store the expiration date each payment extended the membership to,
and display it in the payment history on the member detail page.

### Design Decision
- Add a `new_expiration_date` field directly on the `Payment` model (not a separate table).
- Rationale: every payment produces exactly one expiration result (1:1 relationship).
  The value is already calculated in `process_payment()` but currently discarded.
- `null=True, blank=True` so historical/imported payments without this data are valid.

### Step 1: Add field to Payment model
- **File:** `members/models.py`
- Add `new_expiration_date = models.DateField(null=True, blank=True)` to the `Payment` class.

### Step 2: Generate and run migration
- `python manage.py makemigrations members`
- `python manage.py migrate`

### Step 3: Backfill existing data (one-time management command)
- **File:** `members/management/commands/backfill_payment_expiration.py` (new)
- For each **active, non-Life member** who has at least one payment:
  - Set `new_expiration_date` on their **most recent payment only** to `member.expiration_date`.
- Skip: Life members, inactive/deceased members, members with no payments.
- This is safe because the member's current `expiration_date` is the direct result
  of their last payment (unless manually edited afterward).
- Run with: `python manage.py backfill_payment_expiration`

### Step 4: Populate field on new payments going forward
- **File:** `members/services.py` → `PaymentService.process_payment()`
- After creating the Payment record, set `payment.new_expiration_date` from
  `payment_data["new_expiration"]` and save.
- This is ~1 line of code; the value is already available in the method.

### Step 5: Display in member detail payment history
- **File:** `members/templates/members/member_detail.html`
- Add "Extended To" column header to the payment history table.
- In each payment row, display `payment.new_expiration_date` formatted as "Mon DD, YYYY",
  or "—" if null (for older payments that weren't backfilled).

### Step 6: Update CSV backup export (if payments are exported)
- **File:** `members/reports/csv_backup.py`
- Include `new_expiration_date` in the payment CSV export if that field is part of the output.

### Edge Cases & Notes
- **Manual expiration edits:** If staff edits expiration via Edit Member form, no payment
  is created, so no payment row is affected. This is expected behavior.
- **Override expiration during payment:** The override value IS the `new_expiration` passed
  to `process_payment()`, so it will be captured correctly.
- **Life members:** Excluded from backfill. If a Life member somehow has payments,
  the field stays null (they don't have meaningful expiration dates).
- **Imported historical payments:** Will have null `new_expiration_date`. Only the most
  recent payment per active non-Life member gets backfilled.

### Files Changed (summary)
| File | Change | ~Lines |
|------|--------|--------|
| `members/models.py` | Add field | 1 |
| migration (auto-generated) | Schema change | auto |
| `members/management/commands/backfill_payment_expiration.py` | New command | ~20 |
| `members/services.py` | Set field in `process_payment()` | 1 |
| `members/templates/members/member_detail.html` | Add column | ~5 |
| `members/reports/csv_backup.py` | Add field to export | ~2 |