May 15, 2026. Edit Payment Feature Plan.

1. Add URL route: `payments/edit/<int:payment_id>/` → `edit_payment_view`
2. Create `edit_payment_view` in `members/views/payments.py`
    a. GET: Load payment by ID, render form pre-populated with date, amount, payment method, receipt number
    b. POST: Validate and update only those four fields — do NOT recalculate member expiration
    c. Staff-only access via @staff_member_required
3. Export new view in `members/views/__init__.py`
4. Create `edit_payment.html` template
    a. Member info header (name, ID, type, expiration) — read-only
    b. Payment list table for the member — selected payment highlighted, each row links to edit that payment
    c. Edit form with date, amount, payment method dropdown, receipt number
    d. Save and Cancel buttons
5. Add "Edit Payment" button to `member_detail.html` in the Payment History card header (next to Filters)
6. Create `tests/test_edit_payment.py` covering:
    a. Access control (staff required)
    b. GET renders form with correct pre-populated data
    c. POST updates payment fields successfully
    d. POST does NOT change member expiration or payment.new_expiration_date
    e. Validation errors (future date, empty receipt, invalid amount)
    f. Edge cases (deceased member, nonexistent payment)

---

March 28, 2026. Things left to do for Tony.

1. Create member reports with three past payments.
2. Create a mechanism for people to pause their membership
3. Add a checkbox on the payment page that includes monthly, six months, and thirteen month dues.
    a. This will require that the member type table gets updated with these amounts or a formula.
4. Add functionality in the payment page that indicates the previous expiration date for each payment listed under the member. It should have an expiration date next to it. Maybe that's only in the payment history, or on that member page. Maybe that actually goes into the payment functionality.
5. Add functionality that tells if the receipt number was already used for a different or same payment.  ie: filter for double entries etc.  
    a. also check if the same member has two payments on the same date even if different receipt number
6. the new payment retaining memory feature is still persisting if I salect new payment.  
7. if entering a new member, and thast member name already exists (first + last) then have a pop up that there is a member name already and ask if that is one that should be reactivated.
8.  add the modified expiration date to the first payment screen.  The confirmation page should be to only confirm and not do do any editing.  They would hit back to edit.  

9. modify the payment screen.  
    a. IF choosing monthly, have a field that asks for the inter number of months, up to 10 defaulting to 1.  as this field is changed the payment amount will change.  (this would involve removing the  +/- buttons).  
    b. Lastly there would be a payment option of "other" and the payment Amount field would be (empty?  have some text enter custom about here?) 
    c. there would be a message near the other button that would state the Expiration date can be selected in the next screen.  

10.  Redo the members type csv download and table schema to include the new columns for 6 month and 1 year radion button selections and billing price points.
