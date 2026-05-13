"""
invoice_void_service.py  —  B-Lite Billing v6
Audit-safe Invoice VOID service.

Rules enforced:
  - Original financial values are NEVER modified (total, items, payment).
  - Invoices are NEVER deleted.
  - VOID is implemented as a status flag (is_voided = 1).
  - All operations are atomic using db_transaction().
  - Inventory stock is restored when a product sale is voided.
  - Full audit trail: void_reason, void_at, void_by are logged.
"""

from __future__ import annotations

import json
from utils import app_log


class VoidError(Exception):
    """Raised when a void operation cannot be completed safely."""


def void_invoice(invoice_number: str, reason: str, user: str) -> dict:
    """
    Mark an invoice as VOID and restore inventory stock atomically.

    Args:
        invoice_number: The invoice number to void (e.g., "INV-00123").
        reason:         Mandatory reason text supplied by the operator.
        user:           Username of the operator performing the void.

    Returns:
        dict with keys: invoice, customer, total, items_restored (count)

    Raises:
        VoidError: If invoice not found, already voided, or transaction fails.
    """
    if not invoice_number or not invoice_number.strip():
        raise VoidError("Invoice number is required.")
    if not reason or not reason.strip():
        raise VoidError("A void reason is mandatory.")
    if not user or not user.strip():
        raise VoidError("Operator username is required for the audit trail.")

    invoice_number = invoice_number.strip()
    reason         = reason.strip()
    user           = user.strip()

    try:
        from db import db_transaction
    except ImportError as e:
        raise VoidError(f"Database module unavailable: {e}")

    with db_transaction() as conn:
        # ── 1. Fetch invoice ────────────────────────────────────────
        row = conn.execute(
            "SELECT * FROM sales_report WHERE invoice = ?",
            (invoice_number,)
        ).fetchone()

        if not row:
            raise VoidError(f"Invoice '{invoice_number}' not found in the system.")

        if row["is_voided"]:
            raise VoidError(
                f"Invoice '{invoice_number}' is already VOID "
                f"(voided on {row['void_at']} by {row['void_by']})."
            )

        customer   = row["name"]
        total      = row["total"]
        items_raw  = row["items_raw"] or ""

        # ── 2. Parse items and restore inventory stock ───────────────
        items_restored = 0
        if items_raw:
            try:
                items = _parse_items_raw(items_raw)
                for item in items:
                    item_type = str(item.get("type", "")).lower()
                    item_name = str(item.get("name", "")).strip()
                    qty       = float(item.get("qty", 0))

                    # Only restore stock for product items, not services
                    if item_type in ("product", "prd", "retail") and item_name and qty > 0:
                        result = conn.execute(
                            "SELECT qty FROM inventory WHERE name = ?",
                            (item_name,)
                        ).fetchone()

                        if result is not None:
                            conn.execute(
                                "UPDATE inventory SET qty = qty + ?, updated = datetime('now') WHERE name = ?",
                                (qty, item_name)
                            )
                            items_restored += 1
                            app_log(
                                f"[void_invoice] Stock restored: '{item_name}' +{qty} "
                                f"(invoice={invoice_number})",
                                "info"
                            )
                        else:
                            # Item no longer exists in inventory — log but don't fail
                            app_log(
                                f"[void_invoice] WARNING: Product '{item_name}' not found in "
                                f"inventory during stock restoration (invoice={invoice_number})",
                                "warning"
                            )
            except Exception as e:
                # Parsing failure must abort the entire transaction
                raise VoidError(f"Failed to parse bill items for stock restoration: {e}")

        # ── 3. Mark invoice as VOID ──────────────────────────────────
        conn.execute(
            """
            UPDATE sales_report
            SET is_voided   = 1,
                void_reason = ?,
                void_at     = datetime('now'),
                void_by     = ?
            WHERE invoice = ?
            """,
            (reason, user, invoice_number)
        )

        # ── 4. Audit log ─────────────────────────────────────────────
        app_log(
            f"[INVOICE_VOIDED] Invoice: {invoice_number} | "
            f"Customer: {customer} | Total: {total} | "
            f"User: {user} | Reason: {reason} | "
            f"Stock items restored: {items_restored}",
            "info"
        )

    return {
        "invoice":         invoice_number,
        "customer":        customer,
        "total":           total,
        "items_restored":  items_restored,
    }


def get_invoice_preview(invoice_number: str) -> dict:
    """
    Fetch invoice details for display in the void dialog (read-only).

    Returns:
        dict with invoice details, or raises VoidError if not found.
    """
    if not invoice_number or not invoice_number.strip():
        raise VoidError("Please enter an invoice number.")

    try:
        from db import get_db
        row = get_db().execute(
            "SELECT * FROM sales_report WHERE invoice = ?",
            (invoice_number.strip(),)
        ).fetchone()
    except Exception as e:
        raise VoidError(f"Database error: {e}")

    if not row:
        raise VoidError(f"Invoice '{invoice_number}' not found.")

    items = []
    if row["items_raw"]:
        try:
            items = _parse_items_raw(row["items_raw"])
        except Exception:
            pass

    return {
        "invoice":    row["invoice"],
        "date":       row["date"],
        "customer":   row["name"],
        "phone":      row["phone"],
        "payment":    row["payment"],
        "total":      row["total"],
        "discount":   row["discount"],
        "items":      items,
        "is_voided":  bool(row["is_voided"]),
        "void_at":    row["void_at"] or "",
        "void_by":    row["void_by"] or "",
        "void_reason": row["void_reason"] or "",
    }


# ─────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────────────────

def _parse_items_raw(items_raw: str) -> list[dict]:
    """
    Parse the items_raw field from sales_report.
    Supports two formats:
      1. JSON array:   [{"name": "Shampoo", "qty": 1, "type": "product"}, ...]
      2. Pipe-delimited: type~name~price~qty|type~name~price~qty|...
    """
    raw = items_raw.strip()
    if not raw:
        return []

    # Try JSON first
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    # Try pipe-delimited format (closing_report legacy format)
    # Format: type~name~price~qty|...
    items = []
    for part in raw.split("|"):
        part = part.strip()
        if not part:
            continue
        segments = part.split("~")
        if len(segments) >= 4:
            items.append({
                "type":  segments[0].strip(),
                "name":  segments[1].strip(),
                "price": segments[2].strip(),
                "qty":   segments[3].strip(),
            })
        elif len(segments) >= 2:
            items.append({
                "type":  "",
                "name":  segments[0].strip(),
                "price": segments[1].strip() if len(segments) > 1 else "0",
                "qty":   "1",
            })
    return items
