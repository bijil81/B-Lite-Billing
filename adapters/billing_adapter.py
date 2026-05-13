"""Compatibility adapter for routing legacy billing into v5 service."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.billing_service import BillingService

def use_v5_billing_db() -> bool:
    return bool(get_settings().get("use_v5_billing_db", False))

def finalize_invoice_v5(payload: dict) -> dict:
    result = BillingService().finalize_invoice(payload)
    # Invalidate customer cache so that credit_limit/current_due
    # always reflect the updated DB values when the Customer screen opens next.
    try:
        from adapters.customer_adapter import _service
        phone = str(payload.get("customer_phone", "") or "").strip()
        _service._invalidate_customer_cache(phone)
    except Exception:
        pass
    try:
        from reports_data import invalidate_report_cache
        invalidate_report_cache()
    except Exception:
        pass
    return result
