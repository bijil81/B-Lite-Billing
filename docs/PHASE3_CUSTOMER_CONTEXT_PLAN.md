# Phase 3 Plan - Customer Context Split

Status: complete

Scope:
- Split customer lookup, customer suggestion matching, membership display data, birthday offer detection, and customer save wrappers from `billing.py`.
- Keep Tkinter widget creation and popup rendering in `billing.py` until pure logic is covered.

## Methods Read
- `_billing_get_customers`
- `_billing_save_customer`
- `_billing_record_visit`
- `_billing_redeem_points`
- `_auto_save_customer`
- `_on_customer_keyrelease`
- `_show_suggestions`
- `_build_suggestion_popup`
- `_hover_suggestion`
- `_move_suggestion_selection`
- `_commit_customer_suggestion`
- `_fill_customer`
- `_hide_suggestions`
- `_hide_suggestions_if_safe`
- `_focus_suggestion`
- `_on_phone_lookup`
- `_check_membership_discount`
- `_check_birthday_offer`

## Extraction Order

### 3A - Pure Customer Rules
Status: complete

Target module:
- `src/blite_v6/billing/customer_context.py`

Functions to create:
- `should_auto_save_customer(phone, name) -> bool`
- `normalize_customer_identity(phone, name, birthday) -> dict`
- `build_v5_customer_payload(phone, name, birthday, existing) -> dict`
- `is_valid_lookup_phone(phone) -> bool`
- `build_phone_lookup_state(phone, customer) -> dict`
- `format_membership_info(membership) -> dict`
- `is_birthday_month(birthday, today) -> bool`

Reason:
- These rules can be tested without Tkinter.
- This reduces hidden business logic inside UI callbacks.

### 3B - Suggestion Matching
Status: complete

Target module:
- `src/blite_v6/billing/customer_suggestions.py`

Functions to create:
- `find_customer_suggestions(customers, field, query, limit=8) -> list`
- `format_customer_suggestion_label(customer_name, phone, points, visits) -> str`
- `clamp_suggestion_index(index, size) -> int`

Reason:
- Current `_show_suggestions` and `_build_suggestion_popup` mix matching, formatting, and Tkinter list rendering.
- Matching can be tested before popup UI is touched.

### 3C - BillingFrame Wrappers
Status: complete

Target file:
- `billing.py`

Change style:
- Keep method names unchanged.
- Replace inline logic with calls to extracted helpers.
- Keep widget updates in `billing.py`.

### 3D - Tests
Status: complete

Target files:
- `tests/test_billing_customer_context.py`
- `tests/test_billing_customer_suggestions.py`
- `tests/test_billing_customer_ui_smoke.py`

Minimum test cases:
- Guest/empty customer should not auto-save.
- Valid customer auto-save payload preserves existing birthday, VIP, and points.
- Phone lookup accepts only 10-digit non-placeholder phone.
- Suggestion search by name is case-insensitive.
- Suggestion search by phone matches phone substring.
- Suggestions are capped at 8.
- Birthday month detection handles valid and empty birthday values.
- Membership info text/font decision matches existing behavior.

## Known Risks
- `_check_birthday_offer` currently assumes `YYYY-MM-DD` style and reads `birthday[5:7]`.
- `_build_suggestion_popup` calls `_billing_get_customers()` once per visible suggestion, which is inefficient and can be unstable if the source changes during rendering.
- Customer-related methods depend on many widget attributes from `_build`, so UI decomposition must wait.

## Phase 3 Exit Gate
- Customer pure helper tests pass.
- Existing focused V6 tests still pass.
- `billing.py` behavior remains wrapper-compatible.
- Ledger updated with exact files changed and test result.

## Phase 3A Result
- Added `src/blite_v6/billing/customer_context.py`.
- Added `tests/test_billing_customer_context.py`.
- Wired these helpers into copied V6 `billing.py`:
  - `_billing_save_customer`
  - `_auto_save_customer`
  - `_on_phone_lookup`
  - `_check_membership_discount`
  - `_check_birthday_offer`
- Verification:
  - AST parse passed for edited Phase 3A files.
  - Focused current V6 tests: 25 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 3B Result
- Added `src/blite_v6/billing/customer_suggestions.py`.
- Added `tests/test_billing_customer_suggestions.py`.
- Wired suggestion helpers into copied V6 `billing.py`:
  - `_show_suggestions`
  - `_build_suggestion_popup`
  - `_hover_suggestion`
  - `_move_suggestion_selection`
  - `_focus_suggestion`
- Preserved Tkinter popup rendering in `billing.py`.
- Improvement:
  - `_build_suggestion_popup` now uses the already-loaded customer snapshot instead of calling `_billing_get_customers()` once per visible suggestion.
- Verification:
  - AST parse passed for edited Phase 3B files.
  - Focused current V6 tests: 30 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.

## Phase 3C Result
- Reviewed all remaining customer wrapper methods in copied V6 `billing.py`.
- Added `tests/test_billing_customer_ui_smoke.py`.
- Smoke shim purpose:
  - prove `billing.py` still delegates customer behavior to Phase 3 helper modules
  - catch accidental removal of wrapper helper calls
  - verify suggestion popup uses cached customer snapshot instead of repeated customer loading
- Decision:
  - Full live Tkinter smoke is postponed until more dependencies are copied into V6.
  - Static wrapper smoke is the safest check at this phase because it does not pull the whole application dependency chain.
- Verification:
  - AST parse passed for `billing.py` and `tests/test_billing_customer_ui_smoke.py`.
  - Focused current V6 tests: 32 passed.
  - No cache or bytecode files left in V6.
  - V5.6 source git status clean.
