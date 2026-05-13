"""Transactional billing workflow for v5 cutover."""

from __future__ import annotations

from db_core.transaction import transaction_scope
from repositories.billing_repo import BillingRepository
from validators.billing_validator import validate_invoice_payload
from services_v5.credit_service import (
    validate_payment_amounts,
    compute_new_due,
    check_credit_limit,
    get_customer_credit_data,
    update_customer_due,
    is_customer_blacklisted,
)
from utils import app_log

class BillingService:

    def __init__(self, billing_repo: BillingRepository | None = None):

        self.billing_repo = billing_repo or BillingRepository()

    @staticmethod
    def _is_due_clearance_item(item: dict) -> bool:
        """Return True for the synthetic line used to settle old customer dues."""
        item_type = str(item.get("item_type", item.get("type", "")) or "").strip().lower()
        item_name = str(item.get("item_name", item.get("name", "")) or "").strip().lower()
        return item_type == "due_clearance" or item_name == "previous due clearance"

    def finalize_invoice(self, payload: dict) -> dict:

        invoice = validate_invoice_payload(payload)

        # STEP 1: Get Payment Data
        net_total = float(invoice.get("net_total", 0.0) or 0.0)
        amount_paid = sum(float(p.get("amount", 0.0) or 0.0) for p in invoice.get("payments", []))
        unpaid_amount = round(net_total - amount_paid, 2)

        # Compute due clearance FIRST so validate_payment_amounts() can use it
        due_clearance_amount = round(sum(
            float(i.get("line_total", 0.0) or 0.0)
            for i in invoice.get("items", [])
            if self._is_due_clearance_item(i)
        ), 2)

        # Guard: reject invalid payment amounts before DB work
        # BUG FIX (2026-05-10): pass due_clearance_amount so the validator
        # correctly allows amount_paid > net_total when customer is settling
        # an old due alongside the current invoice.
        validate_payment_amounts(amount_paid, net_total, due_clearance_amount)

        customer_phone = str(invoice.get("customer_phone", "") or "").strip()
        credit_warning = None

        with transaction_scope() as conn:
            # STEP 2 & 3: Skip guest, otherwise fetch data if there's unpaid amount or due clearance
            if customer_phone and customer_phone != "0000000000" and (unpaid_amount != 0 or due_clearance_amount > 0):
                customer = get_customer_credit_data(conn, customer_phone)

                if customer:
                    override_blacklist = invoice.get("override_blacklist", False)
                    # STEP 3b: Block blacklisted customers from credit billing
                    if customer["is_blacklisted"] and unpaid_amount > 0 and not override_blacklist:
                        raise ValueError(
                            "Customer is blacklisted. Credit not allowed. "
                            "Full payment is required."
                        )

                    current_due = customer["current_due"]
                    credit_limit = customer["credit_limit"]

                    # STEP 4: Compute New Due (via credit_service — float-safe)
                    new_due = compute_new_due(current_due, unpaid_amount, due_clearance_amount)

                    # STEP 5: Apply credit limit rules
                    try:
                        warning = check_credit_limit(new_due, credit_limit, unpaid_amount)
                        if warning:
                            credit_warning = warning
                    except ValueError as e:
                        if override_blacklist:
                            credit_warning = f"Credit limit exceeded (Overridden)"
                        else:
                            raise

                    # STEP 6: Final integrity guard before writing
                    if new_due < 0:
                        app_log(f"[billing_service] Anomaly: new_due={new_due} for phone={customer_phone}; clamping to 0")
                        new_due = 0.0
                    if credit_limit > 0 and new_due > credit_limit:
                        app_log(f"[billing_service] Anomaly: new_due={new_due} exceeds credit_limit={credit_limit} for phone={customer_phone}")

                    # STEP 7: Write new due
                    update_customer_due(conn, customer["id"], new_due)

            self._validate_stock_availability(conn, invoice["items"])

            invoice_id = self.billing_repo.create_invoice(conn, invoice)

            item_ids = []

            for item in invoice["items"]:

                item_id = self.billing_repo.add_invoice_item(conn, invoice_id, item)

                item_ids.append(item_id)

                self._record_inventory_movement(conn, invoice["invoice_no"], item)

                self._record_staff_commission(conn, item_id, invoice["invoice_date"], item)

            for payment in invoice["payments"]:

                self.billing_repo.add_payment(conn, invoice_id, payment)

            self._apply_wallet_payments(conn, invoice)
            self._record_loyalty(conn, invoice)

            self._record_redeem_usage(conn, invoice)

            result = {

                "ok": True,

                "invoice_id": invoice_id,

                "invoice_no": invoice["invoice_no"],

                "item_ids": item_ids,

            }

            if credit_warning:

                result["credit_warning"] = credit_warning

            return result

    def _apply_wallet_payments(self, conn, invoice: dict) -> None:
        """Deduct wallet payments atomically with invoice finalization."""
        wallet_total = round(sum(
            float(p.get("amount", 0.0) or 0.0)
            for p in invoice.get("payments", [])
            if str(p.get("payment_method", "")).strip().lower() == "wallet"
        ), 2)
        if wallet_total <= 0:
            return

        invoice_no = str(invoice.get("invoice_no", "") or "").strip()
        customer_phone = str(invoice.get("customer_phone", "") or "").strip()
        if not customer_phone or customer_phone == "0000000000":
            raise ValueError("Wallet payment requires a saved customer phone.")

        duplicate = conn.execute(
            """
            SELECT id FROM v5_membership_transactions
            WHERE customer_phone = ? AND txn_type = 'wallet_redeem' AND reference_id = ?
            """,
            (customer_phone, invoice_no),
        ).fetchone()
        if duplicate:
            return

        membership = conn.execute(
            """
            SELECT id, COALESCE(wallet_balance, 0.0) AS wallet_balance, status
            FROM v5_customer_memberships
            WHERE customer_phone = ?
            """,
            (customer_phone,),
        ).fetchone()
        if not membership:
            raise ValueError("No active membership wallet found for this customer.")

        status = str(membership["status"] or "").strip().lower()
        if status != "active":
            raise ValueError("Wallet cannot be used for inactive/expired membership.")

        balance = float(membership["wallet_balance"] or 0.0)
        if wallet_total > balance + 0.001:
            raise ValueError(f"Insufficient wallet balance. Available: Rs{balance:.2f}")

        new_balance = round(max(0.0, balance - wallet_total), 2)
        conn.execute(
            "UPDATE v5_customer_memberships SET wallet_balance = ?, updated_at = datetime('now') WHERE id = ?",
            (new_balance, membership["id"]),
        )
        conn.execute(
            """
            INSERT INTO v5_membership_transactions(
                customer_membership_id, customer_phone, txn_type, amount, note, reference_id
            ) VALUES(?, ?, 'wallet_redeem', ?, ?, ?)
            """,
            (
                membership["id"],
                customer_phone,
                -wallet_total,
                f"Wallet used for invoice {invoice_no}; balance Rs{new_balance:.2f}",
                invoice_no,
            ),
        )

    def _validate_stock_availability(self, conn, items: list[dict]) -> None:
        """Phase 1: Strict negative stock blocking at service layer."""

        variant_requests = {}

        inventory_requests = {}

        for item in items:

            mode = item.get("mode")

            if mode != "products":

                continue

            qty = float(item.get("qty", 1.0) or 1.0)

            if qty <= 0:

                continue

            variant_id = int(item.get("variant_id", 0) or 0)

            if variant_id:

                variant_requests[variant_id] = variant_requests.get(variant_id, 0.0) + qty

                continue

            inventory_name = str(item.get("inventory_item_name", item.get("name", "")) or "").strip()

            if inventory_name:

                inventory_requests[inventory_name] = inventory_requests.get(inventory_name, 0.0) + qty

        # 1. Validate v5 variants

        for vid, requested_qty in variant_requests.items():

            row = conn.execute("SELECT stock_qty, name FROM v5_product_variants WHERE id = ?", (vid,)).fetchone()

            if row:

                stock_qty = float(row["stock_qty"] or 0.0)

                if stock_qty < requested_qty:

                    raise ValueError(f"Insufficient stock for item: {row['name']}")

        # 2. Validate legacy inventory items

        for inv_name, requested_qty in inventory_requests.items():

            row = conn.execute("SELECT current_qty FROM v5_inventory_items WHERE legacy_name = ? COLLATE NOCASE", (inv_name,)).fetchone()

            if row:

                current_qty = float(row["current_qty"] or 0.0)

                if current_qty < requested_qty:

                    raise ValueError(f"Insufficient stock for item: {inv_name}")

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

        """Record stock deduction for a sale.

        Phase 4 safety: Both UPDATE statements include a WHERE qty >= ? clause.

        If rowcount == 0 after the UPDATE, another concurrent transaction already

        deducted stock → raise ValueError to trigger full rollback.

        """

        if self._is_due_clearance_item(item):
            return

        variant_id = int(item.get("variant_id", 0) or 0)
        qty = float(item.get("qty", 1.0) or 1.0)

        item_label = str(item.get("item_name", item.get("inventory_item_name", "")) or "").strip()

        if variant_id:

            # Phase 4: guarded UPDATE — only deduct if stock is sufficient

            cursor = conn.execute(

                "UPDATE v5_product_variants "

                "SET stock_qty = COALESCE(stock_qty, 0) - ?, updated_at = datetime('now') "

                "WHERE id = ? AND COALESCE(stock_qty, 0) >= ?",

                (qty, variant_id, qty),

            )

            if cursor.rowcount == 0:

                # Stock was depleted between validation and write (race condition)

                row = conn.execute(

                    "SELECT name FROM v5_product_variants WHERE id = ?", (variant_id,)

                ).fetchone()

                name = row["name"] if row else f"variant #{variant_id}"

                raise ValueError(f"Insufficient stock for item: {name}")

            conn.execute(

                "INSERT INTO v5_product_variant_movements"

                "(variant_id, movement_type, qty_delta, reference_type, reference_id, note) "

                "VALUES(?, 'sale', ?, 'invoice', ?, ?)",

                (variant_id, -qty, invoice_no, item_label),

            )

        inventory_name = str(item.get("inventory_item_name", "") or "").strip()

        if not inventory_name:

            return

        inventory = conn.execute(
            # BUG FIX (2026-05-10): Added COLLATE NOCASE to match
            # _validate_stock_availability() which already uses COLLATE NOCASE.
            # Without this, stock validation could pass (case-insensitive) but
            # deduction would silently fail (case-sensitive) — phantom stock.
            "SELECT id FROM v5_inventory_items WHERE legacy_name = ? COLLATE NOCASE",
            (inventory_name,),
        ).fetchone()

        if not inventory:

            return

        # Phase 4: guarded UPDATE — only deduct if stock is sufficient

        cursor = conn.execute(

            "UPDATE v5_inventory_items "

            "SET current_qty = COALESCE(current_qty, 0) - ?, updated_at = datetime('now') "

            "WHERE id = ? AND COALESCE(current_qty, 0) >= ?",

            (qty, inventory["id"], qty),

        )

        if cursor.rowcount == 0:

            raise ValueError(f"Insufficient stock for item: {inventory_name}")

        conn.execute(

            "INSERT INTO v5_inventory_movements"

            "(item_id, movement_type, qty_delta, reference_type, reference_id, note) "

            "VALUES(?, 'sale', ?, 'invoice', ?, ?)",

            (inventory["id"], -qty, invoice_no, item_label or inventory_name),

        )

    def _record_staff_commission(self, conn, invoice_item_id: int, invoice_date: str, item: dict) -> None:

        if self._is_due_clearance_item(item):
            return

        staff_name = str(item.get("staff_name", item.get("staff", "")) or "").strip()
        if not staff_name:

            return

        staff = conn.execute(

            "SELECT commission_pct FROM v5_staff WHERE legacy_name = ? OR display_name = ? LIMIT 1",

            (staff_name, staff_name),

        ).fetchone()

        if not staff:
            # BUG FIX (2026-05-10): Previously silently returned when staff not
            # found in v5_staff — commission was permanently lost with no trace.
            # Now logs a warning so owner can identify name mismatches.
            app_log(
                f"[billing_service] Commission SKIPPED: staff '{staff_name}' not found "
                f"in v5_staff (checked legacy_name and display_name). "
                f"Check for spelling or case mismatch in staff records.",
                "warning",
            )
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
