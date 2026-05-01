# Window Flash Audit

Date: 2026-04-30

## Finding

The remaining white flash risk is mostly from custom `tk.Toplevel` dialogs that are shown by Tk before their dark widgets are fully built. Native Windows dialogs from `messagebox`, `filedialog`, and `simpledialog` may also flash in the OS light theme; those are outside the app theme unless they are replaced with custom dialogs.

## Fixed Now

- `licensing/ui_gate.py` activation dialog now uses the app lifecycle helper:
  - hide window immediately after `Toplevel` creation
  - build widgets while hidden
  - fit/center the dialog
  - reveal only when ready
- Build-prep pass also applied the same helper to app-owned custom windows in:
  - `activity_log.py`
  - `admin.py`
  - `ai_assistant/ui/ai_chat_window.py`
  - `appointments.py`
  - `billing.py`
  - `booking_calendar.py`
  - `customers.py`
  - `dashboard.py`
  - `expenses.py`
  - `help_system.py`
  - `inventory.py`
  - `membership.py`
  - `notifications.py`
  - `offers.py`
  - `reports.py`
  - `staff.py`

## Remaining Light-Theme Cases

- Native `messagebox`, `filedialog`, and `simpledialog` are still OS dialogs and may appear in the Windows light theme.
- Small autocomplete suggestion popups use `overrideredirect`; they are quick inline popups, not the full white-window flash seen during main dialog creation.

## Recommended Pattern

Use `src.blite_v6.app.window_lifecycle.hide_while_building(window)` immediately after creating a `Tk` or `Toplevel`, then call `reveal_when_ready(window)` only after widgets, geometry, transient state, and centering are complete.

## Scope Note

Do not replace every `messagebox` or `filedialog` in one pass. That is a larger UI consistency phase and can change workflows. Prioritize custom app-owned windows first because they can be fixed safely without changing behavior.
