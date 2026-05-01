"""Runtime bridge helpers used by the billing UI coordinator."""

from __future__ import annotations

from adapters.customer_adapter import use_v5_customers_db
from adapters.product_catalog_adapter import get_billing_services_products_snapshot
from customers import (
    add_or_update_customer,
    get_customers,
    record_visit,
    redeem_points,
    save_customers,
)
from services_v5.customer_service import CustomerService
from src.blite_v6.billing.customer_context import (
    build_v5_customer_payload,
    normalize_customer_identity,
    should_auto_save_customer,
)
from ui_theme import _contrast_text
from utils import C


_customer_service = CustomerService()


def billing_entry_fg(preferred: str | None = None) -> str:
    contrast = _contrast_text(C["input"], light=C["text"], dark="#111827")
    if preferred and contrast == C["text"]:
        return preferred
    return contrast


def billing_card_fg(preferred: str | None = None) -> str:
    contrast = _contrast_text(C["card"], light=C["text"], dark="#111827")
    if preferred and contrast == C["text"]:
        return preferred
    return contrast


def billing_get_customers() -> dict:
    if use_v5_customers_db():
        return _customer_service.build_legacy_customer_map()
    return get_customers()


def billing_save_customer(phone: str, name: str, birthday: str = "") -> None:
    if use_v5_customers_db():
        existing = _customer_service.get_customer_by_phone(phone) or {}
        _customer_service.save_customer(build_v5_customer_payload(phone, name, birthday, existing))
        return
    add_or_update_customer(phone, name)
    if birthday.strip():
        merged = get_customers()
        existing = merged.get(phone, {})
        merged[phone] = {
            **existing,
            "name": name,
            "phone": phone,
            "birthday": birthday.strip(),
        }
        save_customers(merged)


def billing_record_visit(phone: str, invoice: str, items: list, total: float, payment: str) -> None:
    if use_v5_customers_db():
        _customer_service.record_visit(phone, invoice, total, payment)
        return
    record_visit(phone, invoice, items, total, payment)


def billing_redeem_points(phone: str, points: int) -> float:
    if use_v5_customers_db():
        return _customer_service.redeem_points(phone, points)
    return redeem_points(phone, points)


def auto_save_customer(phone: str, name: str, birthday: str = ""):
    """Silently create/update customer in DB on every bill action."""
    if not should_auto_save_customer(phone, name):
        return
    identity = normalize_customer_identity(phone, name, birthday)
    billing_save_customer(identity["phone"], identity["name"], identity["birthday"])


def load_services_products():
    return get_billing_services_products_snapshot()
