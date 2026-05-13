# Phase 1 Page/Function Map (2026-05-03)

This is an implementation inventory for writing the step-by-step user guide.

## Main Navigation Pages
- Dashboard -> `dashboard.py` -> `DashboardFrame` (15 methods)
- Billing -> `billing.py` -> `BillingFrame` (98 methods)
- Customers -> `customers.py` -> `CustomersFrame` (34 methods)
- Appointments -> `booking_calendar.py` -> `BookingCalendarFrame` (38 methods)
- Memberships -> `membership.py` -> `MembershipFrame` (18 methods)
- Offers -> `offers.py` -> `OffersFrame` (12 methods)
- Redeem -> `redeem_codes.py` -> `RedeemCodesFrame` (21 methods)
- Cloud Sync -> `cloud_sync.py` -> `CloudSyncFrame` (33 methods)
- Staff -> `staff.py` -> `StaffFrame` (26 methods)
- Inventory -> `inventory.py` -> `InventoryFrame` (38 methods)
- Expenses -> `expenses.py` -> `ExpensesFrame` (20 methods)
- Bulk WhatsApp -> `whatsapp_bulk.py` -> `WhatsAppBulkFrame` (20 methods)
- Reports -> `reports.py` -> `ReportsFrame` (64 methods)
- Closing Report -> `closing_report.py` -> `ClosingReportFrame` (21 methods)
- Settings -> `salon_settings.py` -> `SettingsFrame` (74 methods)

## App Container
- `main.py` -> `SalonApp` (47 methods)
- Handles login handoff, role access, frame switching, runtime preferences, session timeout.

## High-Complexity Pages (Guide Priority)
1. Billing (`BillingFrame`)
   - Search/catalog, cart operations, coupon/redeem flows, payment flow, save/print/whatsapp.
2. Reports (`ReportsFrame`)
   - Sales list, charts, saved bills, service report, grocery report, exports, delete/restore.
3. Settings (`SettingsFrame`)
   - Multi-tab configuration, billing/GST controls, feature flags, backup/license/admin options.
4. Inventory (`InventoryFrame`)
   - Product master, import, purchase, vendor, quick stock update, delete/restore.

## Functional Clusters for User Guide Writing
- Billing lifecycle:
  - select customer -> add items -> discount/redeem -> payment mode -> save/print/share.
- Inventory lifecycle:
  - create/edit product -> stock update -> import/purchase -> vendor management.
- Reporting lifecycle:
  - filter date/search -> inspect list -> export -> charts -> restore deleted bills.
- Admin/config lifecycle:
  - settings tabs -> security/license -> backup/update config -> rollout flags.

## Data Modules to Explain in Guide
- `utils.py` path and helper model (now SQLite-first for selected legacy assets).
- `db.py` kv-store bridge + migration bootstrap.
- `db_core/` + `repositories/` + `services_v5/` layering.
- `adapters/` compatibility switches (v5 rollout toggles).
