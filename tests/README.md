# Test Files for Refactoring Steps

This directory contains test files corresponding to each step of the refactoring process outlined in `docs/REFACTORING_RECOMMENDATIONS.md`.

**Current Status:** ✅ All tests passing (18 tests)

## Test Files Overview

### 1. `test_utils.py` - Step 1: Extract Utility Functions
**Status:** ✅ **8 tests passing**

Tests the date utility functions currently in `members/views.py`:
- `ensure_end_of_month()` - 6 tests
- `add_months_to_date()` - 2 tests

**What it tests:**
- Date calculations for end of month
- Adding months to dates
- Leap year handling
- Year boundary crossings

**Note:** Currently imports from `members.views`. After Step 1 refactoring, update imports to `members.utils`.

**Run:** `uv run pytest tests/test_utils.py -v`

---

### 2. `test_pdf_generation.py` - Step 2: Extract PDF Generation
**Status:** ✅ **1 test passing**

Basic test to verify PDF generation function exists:
- `generate_members_pdf()` function exists and is callable

**Note:** Currently imports from `members.views`. After Step 2 refactoring, update imports to `members.reports.pdf`. More comprehensive tests will be added after refactoring.

**Run:** `uv run pytest tests/test_pdf_generation.py -v`

---

### 3. `test_payment_service.py` - Step 3: Extract Payment Service
**Status:** ✅ **2 tests passing** (placeholder tests)

Placeholder tests that verify PaymentService doesn't exist yet:
- Verifies `PaymentService` import fails (expected before Step 3)

**What will be tested after Step 3:**
- `PaymentService.calculate_expiration()`
- `PaymentService.process_payment()`

**Note:** These tests will be expanded once `members.services.PaymentService` is created.

**Run:** `uv run pytest tests/test_payment_service.py -v`

---

### 4. `test_member_service.py` - Step 4: Extract Member Service
**Status:** ✅ **2 tests passing** (placeholder tests)

Placeholder tests that verify MemberService doesn't exist yet:
- Verifies `MemberService` import fails (expected before Step 4)

**What will be tested after Step 4:**
- `MemberService.get_suggested_ids()`
- `MemberService.create_member()`

**Note:** These tests will be expanded once `members.services.MemberService` is created.

**Run:** `uv run pytest tests/test_member_service.py -v`

---

### 5. `test_member_with_payment.py` - Step 5: Add Payment to Member Creation
**Status:** ✅ **1 test passing** (placeholder test)

Placeholder test for the new feature:
- Basic test structure ready for when feature is implemented

**What will be tested after Step 5:**
- Adding payment when creating a member
- Payment updates member expiration correctly
- No code duplication (uses PaymentService)

**Note:** This test will be expanded once the feature is implemented.

**Run:** `uv run pytest tests/test_member_with_payment.py -v`

---

### 6. `test_views.py` - Step 6: Split Views
**Status:** ✅ **2 tests passing**

Basic integration tests for views:
- Verifies all view functions exist
- Verifies all URLs are configured correctly

**What it tests:**
- `landing_view`, `search_view`, `member_detail_view`
- `add_member_view`, `add_payment_view`
- `current_members_report_view`
- URL routing for all views

**Note:** These tests validate views work correctly regardless of file organization. They will continue to work after Step 6 refactoring.

**Run:** `uv run pytest tests/test_views.py -v`

---

## Running Tests

### Run All Tests
```bash
uv run pytest tests/ -v
```

**Expected Result:** 18 passed, 0 failed

### Run Specific Test Files
```bash
# Step 1: Utility functions
uv run pytest tests/test_utils.py -v

# Step 2: PDF generation
uv run pytest tests/test_pdf_generation.py -v

# Step 3: Payment service (placeholder)
uv run pytest tests/test_payment_service.py -v

# Step 4: Member service (placeholder)
uv run pytest tests/test_member_service.py -v

# Step 5: Member with payment (placeholder)
uv run pytest tests/test_member_with_payment.py -v

# Step 6: Views integration
uv run pytest tests/test_views.py -v
```

### Run with Markers
```bash
# Unit tests only
uv run pytest tests/ -m unit -v

# Integration tests only
uv run pytest tests/ -m integration -v
```

---

## Current Test Summary

| Test File | Tests | Status | Description |
|-----------|-------|--------|-------------|
| `test_utils.py` | 8 | ✅ Passing | Date utility functions |
| `test_pdf_generation.py` | 1 | ✅ Passing | PDF function exists |
| `test_payment_service.py` | 2 | ✅ Passing | Placeholder (service doesn't exist yet) |
| `test_member_service.py` | 2 | ✅ Passing | Placeholder (service doesn't exist yet) |
| `test_member_with_payment.py` | 1 | ✅ Passing | Placeholder (feature not implemented yet) |
| `test_views.py` | 2 | ✅ Passing | View and URL verification |
| `test_database.py` | 2 | ✅ Passing | Database connectivity |
| **Total** | **18** | **✅ All Passing** | |

---

## Test Configuration

### `conftest.py`
- Configures Django settings before imports
- Overrides static files storage for tests (avoids manifest issues)

### `pytest.ini`
- Configured for Django testing
- Uses `pytest-django` plugin
- Test discovery patterns configured

---

## Test Strategy

### Current State (Before Refactoring)
1. ✅ `test_utils.py` - Tests current utility functions in `views.py`
2. ✅ `test_pdf_generation.py` - Verifies PDF function exists
3. ✅ `test_views.py` - Verifies views and URLs exist
4. ✅ `test_payment_service.py` - Placeholder (verifies service doesn't exist)
5. ✅ `test_member_service.py` - Placeholder (verifies service doesn't exist)
6. ✅ `test_member_with_payment.py` - Placeholder (ready for feature)

### After Each Refactoring Step
1. **After Step 1:** Update `test_utils.py` imports to `members.utils` → tests should still pass
2. **After Step 2:** Update `test_pdf_generation.py` imports to `members.reports.pdf` → expand tests
3. **After Step 3:** Expand `test_payment_service.py` → tests should now pass with actual service
4. **After Step 4:** Expand `test_member_service.py` → tests should now pass with actual service
5. **After Step 5:** Expand `test_member_with_payment.py` → tests new feature
6. **After Step 6:** `test_views.py` should still pass (no changes needed)

---

## Notes

- All tests use **pytest** as the test framework
- Django test utilities (`Client`, `RequestFactory`) are used as helper classes (not a test framework)
- Tests are designed to work incrementally as refactoring progresses
- Placeholder tests verify expected state before refactoring
- Tests will be expanded as refactoring steps are completed
- See `docs/TESTING_METHODOLOGY.md` for explanation of pytest + Django approach

---

## Next Steps

1. Start Step 1 refactoring (extract utilities)
2. Update `test_utils.py` imports after Step 1
3. Run tests after each step to validate changes
4. Expand tests as services are created

