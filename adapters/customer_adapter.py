"""Compatibility adapter for gradually moving old UI code to v5 services."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.customer_service import CustomerService


_service = CustomerService()


def use_v5_customers_db() -> bool:
    return bool(get_settings().get("use_v5_customers_db", False))


def list_customers_v5():
    return _service.list_customers()


def get_customer_by_phone_v5(phone: str):
    return _service.get_customer_by_phone(phone)


def get_customers_legacy_map_v5() -> dict:
    return _service.build_legacy_customer_map()


def get_customer_history_v5(phone: str) -> list[dict]:
    return _service.get_customer_history(phone)


def get_deleted_customers_v5() -> list[dict]:
    """Return soft-deleted customers for the Deleted Customers dialog."""
    from soft_delete import get_deleted_customers
    return get_deleted_customers()


def save_customer_v5(payload: dict) -> None:
    _service.save_customer(payload)


def delete_customer_v5(phone: str) -> None:
    """Soft-delete: sets is_deleted flag instead of hard delete."""
    try:
        from soft_delete import soft_delete_customer
        soft_delete_customer(phone, deleted_by="")
        _service._invalidate_customer_cache(phone)
    except Exception:
        _service.delete_customer(phone)


def soft_delete_customer_v5(phone: str, deleted_by: str = "") -> bool:
    """Explicit soft-delete wrapper used by customer UI dialogs."""
    from soft_delete import soft_delete_customer
    ok = soft_delete_customer(phone, deleted_by=deleted_by)
    if ok:
        _service._invalidate_customer_cache(phone)
    return ok


def restore_customer_v5(phone: str) -> bool:
    """Restore a soft-deleted customer and invalidate cache."""
    from soft_delete import restore_customer
    ok = restore_customer(phone)
    if ok:
        _service._invalidate_customer_cache(phone)
    return ok


def permanent_delete_customer_v5(phone: str) -> bool:
    from soft_delete import permanent_delete_customer
    return permanent_delete_customer(phone)


def set_customer_vip_v5(phone: str, vip: bool) -> None:
    _service.set_vip(phone, vip)


def set_customer_points_v5(phone: str, points_balance: int) -> None:
    _service.set_points_balance(phone, points_balance)


def record_visit_v5(phone: str, invoice_no: str, amount: float, payment: str = "") -> int:
    return _service.record_visit(phone, invoice_no, amount, payment)


def redeem_points_v5(phone: str, points: int) -> float:
    return _service.redeem_points(phone, points)
