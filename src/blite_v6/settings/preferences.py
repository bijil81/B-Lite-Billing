from __future__ import annotations

from typing import Mapping


def build_preferences_payload(
    current_settings: Mapping,
    *,
    default_payment: str,
    show_points_on_bill: bool,
    auto_clear_after_print: bool,
    show_whatsapp_confirm: bool,
    show_ai_floating_button: bool,
    enable_animations: bool,
    use_v5_customers_db: bool,
    use_v5_appointments_db: bool,
    use_v5_reports_db: bool,
    use_v5_billing_db: bool,
    use_v5_inventory_db: bool,
    use_v5_staff_db: bool,
    use_v5_product_variants_db: bool,
    start_with_windows: bool,
    default_report_period: str,
    show_below_cost_alert: bool = True,
) -> dict:
    cfg = dict(current_settings)
    cfg["default_payment"] = str(default_payment)
    cfg["show_points_on_bill"] = bool(show_points_on_bill)
    cfg["auto_clear_after_print"] = bool(auto_clear_after_print)
    cfg["show_whatsapp_confirm"] = bool(show_whatsapp_confirm)
    cfg["show_ai_floating_button"] = bool(show_ai_floating_button)
    cfg["enable_animations"] = bool(enable_animations)
    cfg["show_below_cost_alert"] = bool(show_below_cost_alert)
    cfg["use_v5_customers_db"] = bool(use_v5_customers_db)
    cfg["use_v5_appointments_db"] = bool(use_v5_appointments_db)
    cfg["use_v5_reports_db"] = bool(use_v5_reports_db)
    cfg["use_v5_billing_db"] = bool(use_v5_billing_db)
    cfg["use_v5_inventory_db"] = bool(use_v5_inventory_db)
    cfg["use_v5_staff_db"] = bool(use_v5_staff_db)
    cfg["use_v5_product_variants_db"] = bool(use_v5_product_variants_db)
    cfg["start_with_windows"] = bool(start_with_windows)
    cfg["default_report_period"] = str(default_report_period)
    return cfg


def preferences_saved_message(*, start_with_windows: bool, startup_ok: bool) -> str:
    msg = "Preferences saved!"
    if start_with_windows and not startup_ok:
        msg += "\n\nCould not set Windows startup (run as admin)."
    return msg
