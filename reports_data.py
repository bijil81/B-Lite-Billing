"""Report data loading and caching helpers."""
from __future__ import annotations

import csv
import os
import time

from db_core.connection import connection_scope
from db_core.schema_manager import ensure_v5_schema
from utils import F_REPORT, app_log, safe_float

_REPORT_CACHE = {}
_REPORT_SOURCE_CACHE = {}
_REPORT_CACHE_MAX_SIZE = 50


def invalidate_report_cache() -> None:
    _REPORT_CACHE.clear()
    _REPORT_SOURCE_CACHE.clear()


def _evict_cache(cache, max_size):
    if max_size and len(cache) > max_size:
        oldest = next(iter(cache))
        cache.pop(oldest, None)


def _get_invoice_audit_map(invoice_nos: list[str]) -> dict[str, dict[str, str]]:
    invoice_keys = [str(inv).strip() for inv in invoice_nos if str(inv).strip()]
    if not invoice_keys:
        return {}
    try:
        ensure_v5_schema()
        placeholders = ",".join("?" for _ in invoice_keys)
        query = f"""
            SELECT invoice_no,
                   COALESCE(created_by, '') AS created_by,
                   COALESCE(substr(invoice_date, 12, 5), '') AS time
            FROM v5_invoices
            WHERE invoice_no IN ({placeholders})
        """
        with connection_scope() as conn:
            rows = conn.execute(query, tuple(invoice_keys)).fetchall()
        return {
            str(row["invoice_no"]).strip(): {
                "created_by": str(row["created_by"] or "").strip(),
                "time": str(row["time"] or "").strip(),
            }
            for row in rows
            if row and row["invoice_no"]
        }
    except Exception as e:
        app_log(f"[_get_invoice_audit_map] {e}")
        return {}


def _get_deleted_invoice_keys_from_audit() -> set[str]:
    try:
        from soft_delete import get_delete_audit_history

        latest_action: dict[str, str] = {}
        for row in get_delete_audit_history("bill", limit=5000):
            invoice_no = str(row.get("entity_key", "")).strip()
            if not invoice_no or invoice_no in latest_action:
                continue
            latest_action[invoice_no] = str(row.get("action", "")).strip().lower()
        return {
            invoice_no
            for invoice_no, action in latest_action.items()
            if action in {"deleted", "permanent_deleted"}
        }
    except Exception as e:
        app_log(f"[_get_deleted_invoice_keys_from_audit] {e}")
        return set()


def _get_cached_report_source_rows() -> tuple[int, list]:
    if not os.path.exists(F_REPORT):
        return 0, []
    try:
        report_mtime = os.path.getmtime(F_REPORT)
    except Exception as e:
        app_log(f"[_get_cached_report_source_rows mtime] {e}")
        return 0, []

    cached = _REPORT_SOURCE_CACHE.get(F_REPORT)
    if cached and cached.get("mtime") == report_mtime:
        return report_mtime, list(cached.get("rows", []))

    rows = []
    try:
        with open(F_REPORT, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            hdr = next(reader, None)
            new = hdr and len(hdr) >= 6
            for row in reader:
                if not row or len(row) < 4:
                    continue
                if new and len(row) >= 6:
                    dt, inv, nm, ph, pm, tot = row[0], row[1], row[2], row[3], row[4], row[5]
                    disc = row[6] if len(row) > 6 else "0"
                    items_raw = row[7] if len(row) > 7 else ""
                    created_by = row[8] if len(row) > 8 else ""
                else:
                    dt, nm, ph, tot = row[0], row[1], row[2], row[3]
                    inv, pm, items_raw, disc = "---", "---", row[4] if len(row) > 4 else "", "0"
                    created_by = ""
                rows.append({
                    "date": dt,
                    "invoice": inv,
                    "name": nm,
                    "phone": ph,
                    "created_by": created_by,
                    "payment": pm,
                    "total": safe_float(tot),
                    "discount": safe_float(disc),
                    "items_raw": items_raw,
                })
    except Exception as e:
        app_log(f"[_get_cached_report_source_rows] {e}")
        rows = []

    audit_map = _get_invoice_audit_map([row.get("invoice", "") for row in rows])
    if audit_map:
        for row in rows:
            audit = audit_map.get(str(row.get("invoice", "")).strip())
            if not audit:
                continue
            if not str(row.get("created_by", "")).strip():
                row["created_by"] = audit.get("created_by", "")
            if not str(row.get("time", "")).strip():
                row["time"] = audit.get("time", "")

    _REPORT_SOURCE_CACHE[F_REPORT] = {"mtime": report_mtime, "rows": rows}
    return report_mtime, list(rows)


def read_report_rows(from_d="", to_d="", search="") -> list:
    from adapters.report_adapter import get_report_rows_v5, use_v5_reports_db

    rows = []
    cache_key = None
    try:
        if use_v5_reports_db():
            cache_key = ("db", from_d, to_d, search)
            cached = _REPORT_CACHE.get(cache_key)
            if cached and (time.time() - cached["time"]) <= 5.0:
                return cached["rows"]
            rows = get_report_rows_v5(from_d, to_d, search)
            _REPORT_CACHE[cache_key] = {"time": time.time(), "rows": rows}
            _evict_cache(_REPORT_CACHE, _REPORT_CACHE_MAX_SIZE)
            return rows

        report_mtime, source_rows = _get_cached_report_source_rows()
        if not source_rows:
            return rows
        deleted_invoice_keys = _get_deleted_invoice_keys_from_audit()

        cache_key = ("csv", from_d, to_d, search, report_mtime)
        cached = _REPORT_CACHE.get(cache_key)
        if cached and (time.time() - cached["time"]) <= 5.0:
            return cached["rows"]

        q = (search or "").lower()
        for row in source_rows:
            dt = row.get("date", "")
            nm = str(row.get("name", ""))
            ph = str(row.get("phone", ""))
            inv = str(row.get("invoice", ""))
            if inv and inv in deleted_invoice_keys:
                continue
            if q and q not in nm.lower() and q not in ph.lower() and q not in inv.lower():
                continue
            if from_d and dt[:10] < from_d:
                continue
            if to_d and dt[:10] > to_d:
                continue
            rows.append(dict(row))
    except Exception as e:
        app_log(f"[read_report_rows] {e}")

    if cache_key is not None:
        _REPORT_CACHE[cache_key] = {"time": time.time(), "rows": rows}
        _evict_cache(_REPORT_CACHE, _REPORT_CACHE_MAX_SIZE)
    return rows
