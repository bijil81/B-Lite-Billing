# Remaining Split Necessity Audit

Date: 2026-04-30
Project: B-Lite management_Billing_V6.0

## 2026-04-30 Update

The broad split phase can be closed as **functionally complete** after the latest source/EXE smoke gates, with one important condition:

- Keep the original top-level wrapper files.
- Do not delete or hard-shrink them during the grocery/retail implementation.
- Continue with new focused modules for new behavior.

Reason:
- `billing.py`, `main.py`, `reports.py`, and `salon_settings.py` still provide public compatibility surfaces used by the app.
- Deleting them would break imports and startup paths.
- Shrinking them aggressively while adding grocery inventory would mix two risks in one phase.

Next justified split target:
- `inventory.py`, and only as part of the Inventory/Grocery implementation.

Detailed grocery plan:
- `docs/INVENTORY_GROCERY_IMPLEMENTATION_BLUEPRINT.md`

## Decision Rule

File size alone is not enough reason to split. A 60-70 KB file can stay as-is if it has one clear responsibility and low change pressure.

Split only when at least one of these is true:

- The file mixes UI, DB/storage, business rules, exports/printing/networking, and side effects.
- The file is frequently changed or likely to receive near-term feature work.
- Bugs are hard to isolate because pure logic cannot be tested without opening Tk UI.
- A safe helper extraction can reduce risk without changing user-facing behavior.

Do not split just to reduce line count.

## Current Large File Snapshot

| File | Size | Lines | Current Decision |
|---|---:|---:|---|
| `billing.py` | 316.6 KB | 2,140 | Already split through Phase 12; keep wrapper until final manual billing smoke passes |
| `reports.py` | 306.5 KB | 1,618 | Already split through Phase 8; keep wrapper until final manual reports smoke passes |
| `salon_settings.py` | 77.5 KB | 1,532 | Already split through Phase 8; manual settings function smoke pending |
| `ui_theme.py` | 64.8 KB | 1,363 | Do not split now |
| `staff.py` | 64.7 KB | 1,303 | Optional later, not required now |
| `main.py` | 64.0 KB | 1,470 | Already split through Phase 8; keep stable wrapper |
| `cloud_sync.py` | 63.4 KB | 1,235 | Optional later, not required now |
| `booking_calendar.py` | 63.0 KB | 1,038 | Optional later, but not before appointment/manual calendar smoke |
| `inventory.py` | 62.3 KB | 1,305 | Audit/prioritize only if product-grocery work continues |
| `admin.py` | 52.7 KB | 1,062 | Optional later, tied to catalog/import work |
| `customers.py` | 47.6 KB | 1,032 | Do not split now unless customer bugs appear |

## Completed Split Areas

### Billing

Status: split complete, manual functional smoke pending.

Keep `billing.py` as the compatibility/wrapper surface until:

- service bill smoke passes
- product bill smoke passes
- barcode smoke passes
- discount/offer/redeem/points smoke passes
- Save/PDF/Print/WhatsApp smoke passes
- duplicate-save guard smoke passes

Do not continue shrinking `billing.py` before that gate.

### Reports

Status: split complete, manual reports smoke pending.

Keep `reports.py` as the compatibility/wrapper surface until:

- Sales list opens
- Saved bills load
- Print selected bill works or gives correct printer dependency message
- PDF/CSV/Excel/GST export paths work
- Delete/restore works
- Charts load

Do not continue shrinking `reports.py` before that gate.

### Main

Status: split complete, manual app-shell smoke pending.

Keep `main.py` stable. No further split now.

### Salon Settings

Status: split complete through Phase 8, manual settings function smoke pending.

Keep `salon_settings.py` stable. No further split now unless manual smoke finds a specific bug.

## Candidate-by-Candidate Decision

### `ui_theme.py`

Decision: **Do not split now.**

Reason:

- Mostly cohesive design-system/widget helper module.
- Large because it contains theme constants, reusable styled widgets, treeview styles, and animation helpers.
- Splitting now would increase import churn across the whole app without improving business stability.

Only split later if:

- theme bugs become frequent
- animation behavior causes crashes
- there is a planned design-system cleanup phase

### `inventory.py`

Decision: **Conditional audit later; no split immediately.**

Reason:

- Inventory is directly connected to future grocery/supermarket work: loose units, stock qty, GST/product variants, purchases/vendors.
- It mixes UI, inventory storage, product catalog adapter, barcode generation, stock deduction, soft delete, and v5 inventory service.
- There is already a small focused test for loose quantity, but not enough coverage for a broad split.

Recommended later phase only if product-side work resumes:

1. Audit inventory data model and current add/edit item workflow.
2. Extract pure product/unit/stock payload helpers first.
3. Add tests for category/unit/gst/stock validations.
4. Keep `InventoryFrame` as wrapper until manual inventory smoke passes.

Do not start this before billing/report/settings/manual smoke unless inventory-specific work is requested.

### Dashboard Graphical Mode

Decision: **Defer until after EXE build/license smoke.**

Reason:

- This is a user-satisfaction improvement, not a current stability blocker.
- It should be added behind a Preferences switch so the existing dashboard remains the safe default.
- It should be implemented as read-only chart/view helpers to avoid affecting billing, inventory, or accounting data.

Recommended later phase:

1. Add `dashboard_view = classic/graphical` setting.
2. Build graphical dashboard in a separate helper module.
3. Use lightweight Tkinter/Canvas charts first.
4. Smoke with empty data, real sales data, dark/light themes, and EXE packaging.

### `staff.py`

Decision: **Optional later, not required now.**

Reason:

- Large single `StaffFrame` with attendance/payroll/commission-like UI and storage.
- No immediate requested feature depends on staff internals.
- Splitting without a staff bug or payroll feature would add risk without payoff.

Split later only if staff attendance/payroll bugs appear.

### `cloud_sync.py`

Decision: **Optional later, not required now.**

Reason:

- Mixes sync config, folder backup, LAN server/test app, threading, UI.
- It has side effects and network-like behavior, so splitting can help eventually.
- But current release stability work is billing/settings/report heavy, not cloud sync.

Split later only as a dedicated Cloud Sync hardening phase.

### `booking_calendar.py`

Decision: **Optional later, not now.**

Reason:

- Contains useful pure helpers for date/time/overlap, DB booking functions, and Tk modal/calendar UI.
- It is a reasonable future split candidate.
- But appointments/calendar behavior should be manually smoked first before refactor.

Split later only if appointment/calendar bugs or scheduling enhancements are planned.

### `admin.py`

Decision: **Optional later, tied to catalog/import work.**

Reason:

- It has product/service admin, imports, inventory sync payloads, and user manager wiring.
- Future retail/grocery catalog expansion may need this.
- Not urgent before manual app smoke.

### `customers.py`

Decision: **Do not split now.**

Reason:

- Large but mostly customer page + customer helper functions.
- Customer logic already has some billing-side wrappers/tests.
- Split only if customer search/history/points bugs are found.

## Recommended Next Step

Do not begin another split immediately.

Next best step is a **V6 integrated smoke gate**:

1. Restore a working Python/pytest environment if possible.
2. Run settings-focused tests and then full suite.
3. Run manual smoke by module:
   - Main navigation
   - Settings functions
   - Billing service/product/barcode/discount/redeem/save/PDF/print/WhatsApp
   - Reports list/saved bill/export/delete/chart
   - Inventory add/edit/stock/loose unit sanity

After that, decide the next work based on actual failures.

## If a Split Must Continue

The only justified next split target is:

**Inventory.py - Phase 0 Audit Only**

Reason:

- It is the only remaining medium-large file directly connected to grocery/product-unit/GST/purchase-vendor future work.

But implementation should not start until an inventory blueprint is approved.

## Final Recommendation

Current broad splitting work should stop here.

Stabilize the split modules with tests and manual smoke first. Future splits should be bug-driven or feature-driven, not size-driven.
