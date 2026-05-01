"""High-level vendor workflow helpers."""
from __future__ import annotations

from services_v5.purchase_service import PurchaseService

from .cost_tracker import list_vendor_summary


class VendorService:
    def __init__(self, purchase_service: PurchaseService | None = None):
        self._purchase = purchase_service or PurchaseService()

    def list_vendors(self, active_only: bool = True) -> list[dict]:
        vendors = self._purchase.list_vendors(active_only=active_only)
        summary_rows = list_vendor_summary(active_only=active_only)
        summary_by_id = {
            int(row.get("id") or 0): row
            for row in summary_rows
            if int(row.get("id") or 0) > 0
        }
        merged: list[dict] = []
        for vendor in vendors:
            vendor_id = int(vendor.get("id") or 0)
            summary = summary_by_id.get(vendor_id, {})
            row = dict(vendor)
            row["purchase_count"] = summary.get("purchase_count", 0)
            row["total_purchase"] = summary.get("total_purchase", 0.0)
            row["last_purchase_date"] = summary.get("last_purchase_date", "")
            row["last_invoice_no"] = summary.get("last_invoice_no", "")
            merged.append(row)
        return merged

    def list_vendor_summary(self, active_only: bool = True) -> list[dict]:
        return list_vendor_summary(active_only=active_only)

    def save_vendor(self, payload: dict) -> dict:
        return self._purchase.save_vendor(payload)

    def deactivate_vendor(self, vendor_id: int) -> None:
        self._purchase.deactivate_vendor(vendor_id)

    def list_purchase_invoices(self, vendor_id: int | None = None) -> list[dict]:
        return self._purchase.list_vendor_purchase_invoices(vendor_id=vendor_id)
