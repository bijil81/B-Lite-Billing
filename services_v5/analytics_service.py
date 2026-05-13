"""
Read-only Analytics Service for fetching dashboard metrics.
All operations must be isolated and use SELECT queries only.
"""
from datetime import date, timedelta

from db import db_transaction
from utils import app_log


def get_daily_revenue_trend(days: int = 7) -> list[dict]:
    """Return zero-filled daily net invoice revenue for the dashboard trend."""
    try:
        days = max(1, int(days or 7))
    except Exception:
        days = 7

    end_day = date.today()
    start_day = end_day - timedelta(days=days - 1)
    query = """
        SELECT substr(i.invoice_date, 1, 10) as day,
               SUM(
                   i.net_total - COALESCE((
                       SELECT SUM(ii.line_total)
                       FROM v5_invoice_items ii
                       WHERE ii.invoice_id = i.id
                         AND (
                             lower(COALESCE(ii.item_type, '')) = 'due_clearance'
                             OR lower(COALESCE(ii.item_name, '')) = 'previous due clearance'
                         )
                   ), 0.0)
               ) as total
        FROM v5_invoices i
        WHERE substr(i.invoice_date, 1, 10) BETWEEN ? AND ?
          AND COALESCE(i.is_deleted, 0) = 0
        GROUP BY substr(i.invoice_date, 1, 10)
        ORDER BY day ASC
    """
    try:
        with db_transaction() as conn:
            rows = conn.execute(query, (start_day.isoformat(), end_day.isoformat())).fetchall()
            totals_by_day = {r["day"]: float(r["total"] or 0) for r in rows}
    except Exception as e:
        app_log(f"[analytics daily revenue trend] {e}")
        totals_by_day = {}

    trend = []
    for offset in range(days):
        current = start_day + timedelta(days=offset)
        key = current.isoformat()
        trend.append({"day": key, "total": totals_by_day.get(key, 0.0)})
    return trend


def get_daily_cashflow_last_30_days() -> list[dict]:
    """Backward-compatible wrapper; dashboard now uses POS-standard 7-day sales trend."""
    return get_daily_revenue_trend(7)

def get_top_selling_items(limit: int = 5) -> list[dict]:
    """Return the most frequently sold items."""
    query = """
        SELECT item_name, SUM(qty) as total_qty
        FROM v5_invoice_items ii
        JOIN v5_invoices i ON i.id = ii.invoice_id
        WHERE COALESCE(i.is_deleted, 0) = 0
          AND lower(COALESCE(ii.item_type, '')) != 'due_clearance'
          AND lower(COALESCE(ii.item_name, '')) != 'previous due clearance'
        GROUP BY item_name
        ORDER BY total_qty DESC
        LIMIT ?
    """
    try:
        with db_transaction() as conn:
            rows = conn.execute(query, (limit,)).fetchall()
            return [{"name": r["item_name"], "qty": int(r["total_qty"] or 0)} for r in rows]
    except Exception as e:
        app_log(f"[analytics top selling items] {e}")
        return []

def get_payment_methods_breakdown() -> list[dict]:
    """Return revenue breakdown by payment method."""
    query = """
        SELECT p.payment_method, SUM(p.amount) as total
        FROM v5_payments p
        JOIN v5_invoices i ON i.id = p.invoice_id
        WHERE COALESCE(i.is_deleted, 0) = 0
        GROUP BY p.payment_method
    """
    try:
        with db_transaction() as conn:
            rows = conn.execute(query).fetchall()
            return [{"method": r["payment_method"], "total": float(r["total"] or 0)} for r in rows]
    except Exception as e:
        app_log(f"[analytics payment methods] {e}")
        return []
