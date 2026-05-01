"""Transactional billing workflow for v5 cutover."""

from __future__ import annotations

from db_core.transaction import transaction_scope
from repositories.billing_repo import BillingRepository
from validators.billing_validator import validate_invoice_payload


class BillingService:
    def __init__(self, billing_repo: BillingRepository | None = None):
        self.billing_repo = billing_repo or BillingRepository()

    def finalize_invoice(self, payload: dict) -> dict:
        invoice = validate_invoice_payload(payload)
        with transaction_scope() as conn:
            invoice_id = self.billing_repo.create_invoice(conn, invoice)
            item_ids = []
            for item in invoice["items"]:
                item_id = self.billing_repo.add_invoice_item(conn, invoice_id, item)
                item_ids.append(item_id)
                self._record_inventory_movement(conn, invoice["invoice_no"], item)
                self._record_staff_commission(conn, item_id, invoice["invoice_date"], item)
            for payment in invoice["payments"]:
                self.billing_repo.add_payment(conn, invoice_id, payment)
            self._record_loyalty(conn, invoice)
            self._record_redeem_usage(conn, invoice)
            return {
                "ok": True,
                "invoice_id": invoice_id,
                "invoice_no": invoice["invoice_no"],
                "item_ids": item_ids,
            }

    def _record_loyalty(self, conn, invoice: dict) -> None:
        phone = str(invoice.get("customer_phone", "") or "").strip()
        if not phone:
            return
        customer = conn.execute(
            "SELECT id FROM v5_customers WHERE legacy_phone = ?",
            (phone,),
        ).fetchone()
        if not customer:
            return
        earned = int(invoice.get("loyalty_earned", 0) or 0)
        redeemed = int(invoice.get("loyalty_redeemed", 0) or 0)
        delta = earned - redeemed
        if delta:
            conn.execute(
                "UPDATE v5_customers SET points_balance = COALESCE(points_balance, 0) + ?, updated_at = datetime('now') WHERE id = ?",
                (delta, customer["id"]),
            )
        if earned:
            conn.execute(
                "INSERT INTO v5_loyalty_ledger(customer_id, txn_type, points_delta, reference_type, reference_id, note) VALUES(?, 'earn', ?, 'invoice', ?, ?)",
                (customer["id"], earned, invoice["invoice_no"], 'Invoice loyalty earned'),
            )
        if redeemed:
            conn.execute(
                "INSERT INTO v5_loyalty_ledger(customer_id, txn_type, points_delta, reference_type, reference_id, note) VALUES(?, 'redeem', ?, 'invoice', ?, ?)",
                (customer["id"], -redeemed, invoice["invoice_no"], 'Invoice loyalty redeemed'),
            )
        conn.execute(
            "INSERT INTO v5_customer_visits(customer_id, visit_date, note, amount, invoice_no) VALUES(?, ?, ?, ?, ?)",
            (customer["id"], invoice["invoice_date"], invoice.get("notes", ""), float(invoice.get("net_total", 0.0) or 0.0), invoice["invoice_no"]),
        )

    def _record_redeem_usage(self, conn, invoice: dict) -> None:
        code = str(invoice.get("redeem_code", "") or "").strip()
        if not code:
            return
        conn.execute(
            "UPDATE v5_redeem_codes SET used = 1, used_invoice = ?, updated_at = datetime('now') WHERE code = ?",
            (invoice["invoice_no"], code),
        )
        conn.execute(
            "INSERT INTO v5_redeem_transactions(code, invoice_no, discount_amount, customer_phone) VALUES(?, ?, ?, ?)",
            (code, invoice["invoice_no"], float(invoice.get("redeem_discount", 0.0) or 0.0), invoice.get("customer_phone", "")),
        )

    def _record_inventory_movement(self, conn, invoice_no: str, item: dict) -> None:
        variant_id = int(item.get("variant_id", 0) or 0)
        qty = float(item.get("qty", 1.0) or 1.0)
        if variant_id:
            conn.execute(
                "UPDATE v5_product_variants SET stock_qty = COALESCE(stock_qty, 0) - ?, updated_at = datetime('now') WHERE id = ?",
                (qty, variant_id),
            )
            conn.execute(
                "INSERT INTO v5_product_variant_movements(variant_id, movement_type, qty_delta, reference_type, reference_id, note) VALUES(?, 'sale', ?, 'invoice', ?, ?)",
                (
                    variant_id,
                    -qty,
                    invoice_no,
                    str(item.get("item_name", item.get("inventory_item_name", "")) or "").strip(),
                ),
            )

        inventory_name = str(item.get("inventory_item_name", "") or "").strip()
        if not inventory_name:
            return
        inventory = conn.execute(
            "SELECT id FROM v5_inventory_items WHERE legacy_name = ?",
            (inventory_name,),
        ).fetchone()
        if not inventory:
            return
        conn.execute(
            "UPDATE v5_inventory_items SET current_qty = COALESCE(current_qty, 0) - ?, updated_at = datetime('now') WHERE id = ?",
            (qty, inventory["id"]),
        )
        conn.execute(
            "INSERT INTO v5_inventory_movements(item_id, movement_type, qty_delta, reference_type, reference_id, note) VALUES(?, 'sale', ?, 'invoice', ?, ?)",
            (inventory["id"], -qty, invoice_no, item.get("item_name", inventory_name)),
        )

    def _record_staff_commission(self, conn, invoice_item_id: int, invoice_date: str, item: dict) -> None:
        staff_name = str(item.get("staff_name", item.get("staff", "")) or "").strip()
        if not staff_name:
            return
        staff = conn.execute(
            "SELECT commission_pct FROM v5_staff WHERE legacy_name = ? OR display_name = ? LIMIT 1",
            (staff_name, staff_name),
        ).fetchone()
        if not staff:
            return
        rate_pct = float(staff["commission_pct"] or 0.0)
        if rate_pct <= 0:
            return
        line_total = float(item.get("line_total", item.get("total", 0.0)) or 0.0)
        amount = round(line_total * rate_pct / 100.0, 2)
        conn.execute(
            "INSERT INTO v5_staff_commissions(staff_name, invoice_item_id, amount, rate_pct, commission_date) VALUES(?, ?, ?, ?, ?)",
            (staff_name, invoice_item_id, amount, rate_pct, invoice_date),
        )
