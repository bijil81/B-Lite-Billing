"""Transactional purchase workflow for inventory/vendor foundation."""

from __future__ import annotations

from db_core.schema_manager import ensure_v5_schema
from db_core.transaction import transaction_scope
from repositories.purchase_repo import PurchaseRepository
from src.blite_v6.inventory_grocery.purchase_validation import (
    validate_purchase_invoice_payload,
    validate_vendor_payload,
)


class PurchaseService:
    def __init__(self, repo: PurchaseRepository | None = None):
        self.repo = repo or PurchaseRepository()

    def list_vendors(self, active_only: bool = True) -> list[dict]:
        return self.repo.list_vendors(active_only=active_only)

    def save_vendor(self, payload: dict) -> dict:
        vendor = validate_vendor_payload(payload)
        vendor["vendor_id"] = int(payload.get("vendor_id") or 0)
        ensure_v5_schema()
        with transaction_scope() as conn:
            vendor_id = self.repo.save_vendor(conn, vendor)
            return {"ok": True, "vendor_id": vendor_id, "vendor_name": vendor["name"]}

    def deactivate_vendor(self, vendor_id: int) -> None:
        self.repo.deactivate_vendor(vendor_id)

    def save_purchase_invoice(self, payload: dict) -> dict:
        invoice = validate_purchase_invoice_payload(payload)
        ensure_v5_schema()
        with transaction_scope() as conn:
            vendor_id = int(invoice.get("vendor_id") or 0)
            if not vendor_id:
                vendor_id = self.repo.upsert_vendor(conn, invoice["vendor"])
            elif not invoice["vendor"].get("name"):
                row = conn.execute("SELECT name FROM v5_vendors WHERE id = ?", (vendor_id,)).fetchone()
                if not row:
                    raise ValueError(f"vendor_id not found: {vendor_id}")
                invoice["vendor"]["name"] = str(row["name"] or "").strip()
            invoice["vendor_id"] = vendor_id
            purchase_id = self.repo.create_purchase_invoice(conn, invoice)
            item_ids = []
            for item in invoice["items"]:
                item["variant_id"] = self._resolve_variant_id(conn, item)
                item_ids.append(self.repo.add_purchase_item(conn, purchase_id, item))
                self._record_stock_receipt(conn, purchase_id, invoice, item)
            return {
                "ok": True,
                "purchase_invoice_id": purchase_id,
                "vendor_id": vendor_id,
                "invoice_no": invoice["invoice_no"],
                "gross_total": invoice["gross_total"],
                "tax_total": invoice["tax_total"],
                "net_total": invoice["net_total"],
                "item_ids": item_ids,
            }

    def list_purchase_invoices(self) -> list[dict]:
        return self.repo.list_purchase_invoices()

    def list_purchase_items(self, purchase_invoice_id: int) -> list[dict]:
        return self.repo.list_purchase_items(purchase_invoice_id)

    def list_vendor_summary(self, active_only: bool = True) -> list[dict]:
        return self.repo.list_vendor_purchase_summary(active_only=active_only)

    def list_vendor_purchase_invoices(self, vendor_id: int | None = None) -> list[dict]:
        return self.repo.list_vendor_purchase_invoices(vendor_id=vendor_id)

    def _resolve_variant_id(self, conn, item: dict) -> int:
        variant_id = int(item.get("variant_id") or 0)
        if variant_id:
            return variant_id
        name = str(item.get("item_name", "")).strip()
        if not name:
            return 0
        row = conn.execute(
            """
            SELECT v.id
            FROM v5_product_variants v
            JOIN v5_catalog_products p ON p.id = v.product_id
            WHERE lower(coalesce(v.bill_label, '')) = lower(?)
               OR lower(coalesce(v.variant_name, '')) = lower(?)
               OR lower(coalesce(v.pack_label, '')) = lower(?)
               OR lower(p.name) = lower(?)
            ORDER BY v.active DESC, v.id
            LIMIT 1
            """,
            (name, name, name, name),
        ).fetchone()
        return int(row["id"]) if row else 0

    def _record_stock_receipt(self, conn, purchase_id: int, invoice: dict, item: dict) -> None:
        qty = float(item.get("qty", 0.0) or 0.0)
        variant_id = int(item.get("variant_id") or 0)
        if variant_id:
            conn.execute(
                """
                UPDATE v5_product_variants
                SET stock_qty = COALESCE(stock_qty, 0) + ?,
                    cost_price = ?,
                    sale_price = CASE WHEN ? > 0 THEN ? ELSE sale_price END,
                    mrp = CASE WHEN ? > 0 THEN ? ELSE mrp END,
                    gst_rate = ?,
                    hsn_sac = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    qty,
                    item["cost_price"],
                    item["sale_price"],
                    item["sale_price"],
                    item["mrp"],
                    item["mrp"],
                    item["gst_rate"],
                    item["hsn_sac"],
                    variant_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO v5_product_variant_movements(
                    variant_id, movement_type, qty_delta, qty_unit, unit_cost,
                    supplier_name, purchase_ref, batch_no, expiry_date,
                    reference_type, reference_id, note
                ) VALUES(?, 'purchase', ?, ?, ?, ?, ?, ?, ?, 'purchase_invoice', ?, ?)
                """,
                (
                    variant_id,
                    qty,
                    item["unit"],
                    item["cost_price"],
                    invoice["vendor"]["name"],
                    invoice["invoice_no"],
                    item["batch_no"],
                    item["expiry_date"],
                    str(purchase_id),
                    item["item_name"],
                ),
            )

        row = conn.execute(
            "SELECT id FROM v5_inventory_items WHERE lower(legacy_name) = lower(?)",
            (item["item_name"],),
        ).fetchone()
        if not row:
            return
        conn.execute(
            """
            UPDATE v5_inventory_items
            SET current_qty = COALESCE(current_qty, 0) + ?,
                unit = ?,
                cost_price = ?,
                sale_price = CASE WHEN ? > 0 THEN ? ELSE sale_price END,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                qty,
                item["unit"],
                item["cost_price"],
                item["sale_price"],
                item["sale_price"],
                row["id"],
            ),
        )
        conn.execute(
            """
            INSERT INTO v5_inventory_movements(
                item_id, movement_type, qty_delta, reference_type, reference_id, note
            ) VALUES(?, 'purchase', ?, 'purchase_invoice', ?, ?)
            """,
            (row["id"], qty, str(purchase_id), invoice["invoice_no"]),
        )
