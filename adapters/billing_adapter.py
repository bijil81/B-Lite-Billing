"""Compatibility adapter for routing legacy billing into v5 service."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.billing_service import BillingService


def use_v5_billing_db() -> bool:
    return bool(get_settings().get("use_v5_billing_db", False))


def finalize_invoice_v5(payload: dict) -> dict:
    return BillingService().finalize_invoice(payload)
