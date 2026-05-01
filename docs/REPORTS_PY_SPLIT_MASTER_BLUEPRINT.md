# Reports.py Split Master Blueprint

Project: B-Lite management_Billing_V6.0
Source under work: reports.py
Stable source rule: do not mutate V5.6. All split work happens in V6 only.

## Goal

Shrink `reports.py` safely without changing the stable app behavior. Reports is a high-risk module because it combines UI layout, report data loading, bill preview reconstruction, saved PDF actions, delete/restore flows, exports, charts, service reports, and print/WhatsApp side effects.

The split must improve maintainability while keeping existing reports behavior stable. Small correctness fixes are allowed only when covered by focused tests and when they do not alter unrelated billing flows.

## Audit Summary

- Current size: about 326 KB and 2,042 lines.
- Primary class: `ReportsFrame`.
- Existing extracted helpers already used:
  - `reports_data.py` for report row loading/cache.
  - `reports_export.py` for CSV/Excel export helpers.
  - `reports_context.py`, `reports_deleted.py`, and `reports_reprint.py` for some report actions.
- Still mixed inside `reports.py`:
  - bill text preview reconstruction
  - list tab UI and selection preview
  - saved PDF list/preview/open/print/WhatsApp actions
  - delete/restore dialogs and context menu callbacks
  - pagination state and loading
  - export center UI wrappers
  - chart rendering
  - service report generation and pagination

## Non-Negotiable Rules

- Preserve app startup path from `main.py`.
- Keep `ReportsFrame` as the public UI entry point until final integration.
- Each phase must leave the app importable.
- Avoid UI rewrites during extraction phases.
- Add tests for extracted pure logic before or with each extraction.
- Do not silently change report totals, invoice IDs, dates, phone numbers, or deleted bill state.
- Do not remove legacy CSV compatibility.
- Clean `__pycache__` and `.pytest_cache` after test runs.

## Phase Plan

### Phase 0 - Audit and Guardrails

Status: complete.

Actions:
- Map function boundaries and call sites.
- Identify lowest-risk pure helper extraction.
- Confirm report tests are currently sparse.

Gate:
- No code behavior changes.

### Phase 1 - Bill Text Preview Builder Extraction

Status: complete.

Target:
- Move top-level `_build_bill_text` out of `reports.py`.
- New module: `src/blite_v6/reports/bill_text.py`.
- Keep compatibility alias in `reports.py` so existing `ReportsFrame` call sites remain unchanged.

Why this first:
- It is pure text building with only settings/branding dependencies.
- It is used from only three places: report selection preview, saved PDF fallback preview, and print preview.
- It can be tested without Tkinter.

Quality fix allowed:
- Preserve decimal quantities in preview text for grocery/loose products instead of truncating them.

Gate:
- Focused tests for old CSV item format, new item format, discount totals, and decimal quantity formatting.
- Full pytest before handoff.

Result:
- Extracted `src/blite_v6/reports/bill_text.py`.
- Kept `reports.py` compatibility alias: `_build_bill_text`.
- Added focused tests in `tests/test_reports_bill_text.py`.

### Phase 2 - Saved Bill File Actions

Status: complete.

Target:
- Extract saved PDF list loading, PDF text preview fallback, open/print/WhatsApp wrappers into a small action/helper module.

Risk:
- File system paths, PDF text extraction, platform open/print behavior.

Gate:
- Tests around path filtering and selected bill metadata parsing.

Result:
- Extracted `src/blite_v6/reports/saved_bills.py`.
- Moved saved PDF filename parsing, directory listing/cache, selected saved bill DTO building, report-row invoice lookup, and PDF text/fallback preview building out of `reports.py`.
- Kept UI dialogs, Treeview wiring, print shell call, WhatsApp thread, and permission checks in `ReportsFrame`.
- Added focused tests in `tests/test_reports_saved_bills.py`.

### Phase 3 - Report Row Loading View Model

Status: complete.

Target:
- Keep raw loading in `reports_data.py`.
- Extract filtering, pagination page slicing, card totals, and selected-row mapping helpers.

Risk:
- Date range and search behavior.

Gate:
- Tests for date boundaries, search matching, deleted bill exclusion, and pagination.

Result:
- Extracted `src/blite_v6/reports/report_view.py`.
- Moved report summary totals, page clamping/slicing, sales Treeview value formatting, and result-label copy out of `reports.py`.
- Kept date validation, `_read_report()` source call, Treeview insertion, preview clearing, and UI button rendering in `ReportsFrame`.
- Added focused tests in `tests/test_reports_view_model.py`.

### Phase 4 - Export Center Wrappers

Status: complete.

Target:
- Move transaction/payment/profit/customer/supplier export orchestration wrappers out of `ReportsFrame`.

Risk:
- Empty result handling and file open side effects.

Gate:
- Mocked tests for result handling and selected customer filters.

Result:
- Extracted `src/blite_v6/reports/export_actions.py`.
- Moved report filter normalization, export result message modeling, selected customer extraction, and standard search/date/customer export call wrappers out of `reports.py`.
- Kept actual Tk dialogs, message boxes, file opening, and export center window UI inside `ReportsFrame`.
- Added focused tests in `tests/test_reports_export_actions.py`.

### Phase 5 - Service Report Builder

Status: complete.

Target:
- Extract service report parsing, aggregation, sorting, and pagination.

Risk:
- Legacy `items_raw` parsing and mixed service/product entries.

Gate:
- Tests for old and new item formats, service totals, quantities, and pagination.

Result:
- Extracted `src/blite_v6/reports/service_report.py`.
- Moved service/product item parsing, aggregation, sorting, decimal quantity handling, page slicing, and Treeview value formatting out of `reports.py`.
- Kept Service Report tab UI, date entry controls, Treeview widgets, and pager button creation inside `ReportsFrame`.
- Added focused tests in `tests/test_reports_service_report.py`.
- Correctness fix: product decimal quantities such as grocery loose-weight sales are no longer truncated in service/product report totals.

### Phase 6 - Delete/Restore and Context Menus

Status: complete.

Target:
- Extract report bill selection DTOs, delete action decisions, restore dialog data handling, and context menu callback registry.

Risk:
- Admin permission checks and soft-delete audit history.

Gate:
- Tests for admin guard, deleted entry shape, and callback routing.

Result:
- Extracted `src/blite_v6/reports/delete_restore.py`.
- Moved report context selected-row building, selected report bill DTO construction, delete prompt/target labeling, admin role checks, deleted-bill Treeview values, DB/trash deleted-entry normalization, audit mapping, and deleted-entry sorting out of `reports.py`.
- Kept message boxes, password prompts, DB soft-delete/restore calls, file moves/removes, and Tk deleted-bills dialog UI inside `ReportsFrame`.
- Added focused tests in `tests/test_reports_delete_restore.py`.
- Removed the legacy inline deleted-entry builder from `reports.py` after replacing it with the helper-backed method.

### Phase 7 - Chart Data Builder

Status: complete.

Target:
- Extract chart aggregation data from Tk drawing.

Risk:
- Visual drawing remains in UI; only data prep should move first.

Gate:
- Tests for daily/monthly buckets and empty rows.

Result:
- Extracted `src/blite_v6/reports/chart_data.py`.
- Moved daily revenue, monthly revenue, payment-method revenue, and top-service revenue series building out of `reports.py`.
- Kept matplotlib figure creation, colors, axes, labels, and Tk canvas embedding inside `ReportsFrame`.
- Added focused tests in `tests/test_reports_chart_data.py`.
- Correctness fix: top-service chart revenue now respects decimal service quantities instead of using integer-only quantity math.

### Phase 8 - Final Integration Shrink

Status: complete.

Target:
- Reduce `reports.py` to `ReportsFrame` shell, tab build orchestration, and thin callback wiring.

Gate:
- Manual smoke: Reports list, row preview, saved bills, PDF open/print fallback, WhatsApp bill, delete/restore, export CSV/Excel/PDF/GST, service report, charts.
- Full pytest.

Result:
- Cleaned the `reports.py` import surface after the helper extractions.
- Kept `ReportsFrame` as the public UI entry point for the app shell.
- Added `tests/test_reports_final_integration_smoke.py` to verify:
  - `reports.py` remains importable.
  - all split report modules remain importable.
  - each extracted responsibility is still wired from `reports.py`.
  - removed legacy unused imports do not return.
- Current `reports.py` size after Phase 8 cleanup: 313,402 bytes / 1,779 lines.
- Verification:
  - `py_compile` passed for `reports.py` and all split Reports helper modules.
  - focused Reports tests: 42 passed.
  - full pytest: 213 passed.

## Manual Smoke Checklist

- Open V6 through `main.py`.
- Navigate to Reports.
- Load today/month/all ranges.
- Search by invoice, customer, and phone.
- Select a row and verify preview text.
- Preview a saved bill PDF and fallback text.
- Export CSV/Excel/PDF/GST.
- Generate service report.
- Open charts tab.
- Delete and restore a test bill using admin account.
- Confirm Billing still opens after Reports changes.

## Current Next Gate

Next phase: live V6 manual Reports smoke gate.

Important:
- The planned Reports.py split phases are complete.
- Do not start another Reports refactor before the live app smoke confirms behavior.
- Keep V5.6 untouched; continue testing from `B-Lite management_Billing_V6.0`.
