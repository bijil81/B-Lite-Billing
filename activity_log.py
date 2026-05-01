"""Activity log — lightweight SQLite table for auditing key actions.

Created for V5.6.1 Phase 1 — Safety & Recovery.
"""
from __future__ import annotations

import json
import sqlite3
import threading

from branding import get_appdata_dir_name
from utils import app_log

_LOG_LOCK = threading.Lock()
_local = threading.local()


def _data_dir() -> str:
    import os
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    root = os.path.join(base, get_appdata_dir_name())
    os.makedirs(root, exist_ok=True)
    return root


def _db_path() -> str:
    import os
    return os.path.join(_data_dir(), "activity_log.db")


def _get_log_conn() -> sqlite3.Connection:
    """Thread-local connection with lazy init and auto-create schema."""
    if hasattr(_local, "conn") and _local.conn is not None:
        try:
            _local.conn.execute("SELECT 1")
            return _local.conn
        except Exception:
            pass
    db_path = _db_path()
    db_exists = db_path and __import__("os").path.exists(db_path)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    if not db_exists:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT    NOT NULL DEFAULT (datetime('now')),
                event      TEXT    NOT NULL,
                entity     TEXT,
                entity_id  TEXT,
                user       TEXT,
                details    TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_log_ts     ON activity_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_log_event  ON activity_log(event);
            CREATE INDEX IF NOT EXISTS idx_log_entity ON activity_log(entity);
            CREATE INDEX IF NOT EXISTS idx_log_user   ON activity_log(user);
        """)
    _local.conn = conn
    return conn


# ── Public API ──────────────────────────────────────────────

EVENT_TYPES = {
    # Bill events
    "bill_created",
    "bill_edited",
    "bill_deleted",
    "bill_voided",
    # Customer events
    "customer_created",
    "customer_edited",
    "customer_deleted",
    # Product/Inventory events
    "product_created",
    "product_edited",
    "product_deleted",
    # Auth events
    "login_success",
    "login_failed",
    "logout",
    # Backup events
    "backup_created",
    "backup_restored",
    "backup_scheduled",
    "backup_schedule_changed",
    # Settings events
    "settings_changed",
    "user_created",
    "user_edited",
    "user_deleted",
}


def log_event(
    event: str,
    entity: str = "",
    entity_id: str = "",
    user: str = "",
    details: dict | None = None,
) -> bool:
    """Write one row to the activity log. Never raises.

    Args:
        event: One of the EVENT_TYPES constants.
        entity: High-level entity type e.g. 'bill', 'customer'.
        entity_id: Invoice number, phone, product key, etc.
        user: Username of the actor.
        details: Optional JSON-serialisable context dict.
    """
    try:
        with _LOG_LOCK:
            conn = _get_log_conn()
            conn.execute(
                """INSERT INTO activity_log
                   (event, entity, entity_id, user, details)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    event,
                    entity,
                    str(entity_id),
                    str(user),
                    json.dumps(details, ensure_ascii=False) if details else "",
                ),
            )
            conn.commit()
        return True
    except Exception as e:
        app_log(f"[activity_log] write failed: {e}")
        return False


def query_events(
    limit: int = 200,
    offset: int = 0,
    event_filter: str = "",
    entity_filter: str = "",
    user_filter: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    """Return activity log rows as dicts, newest first."""
    try:
        with _LOG_LOCK:
            conn = _get_log_conn()
            conditions: list[str] = []
            params: list = []

            if event_filter:
                conditions.append("event = ?")
                params.append(event_filter)
            if entity_filter:
                conditions.append("entity = ?")
                params.append(entity_filter)
            if user_filter:
                conditions.append("user = ? ")
                params.append(user_filter)
            if date_from:
                conditions.append("timestamp >= ?")
                params.append(date_from)
            if date_to:
                conditions.append("timestamp <= ?")
                params.append(date_to)

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            sql = f"""
                SELECT id, timestamp, event, entity, entity_id,
                       user, details
                FROM activity_log
                {where}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        app_log(f"[activity_log.query_events] {e}")
        return []


def get_event_count() -> int:
    """Total number of log entries."""
    try:
        with _LOG_LOCK:
            conn = _get_log_conn()
            row = conn.execute("SELECT COUNT(*) AS c FROM activity_log").fetchone()
            return row["c"] if row else 0
    except Exception as e:
        app_log(f"[activity_log.count] {e}")
        return 0


def purge_older_than(days: int = 90) -> int:
    """Delete log entries older than N days."""
    try:
        with _LOG_LOCK:
            conn = _get_log_conn()
            cur = conn.execute(
                "DELETE FROM activity_log WHERE timestamp < datetime('now', ?)",
                (f"-{days} days",),
            )
            conn.commit()
            return cur.rowcount
    except Exception as e:
        app_log(f"[activity_log.purge] {e}")
        return 0


# ── Activity Log Viewer UI ─────────────────────────────────

def show_activity_log_viewer(parent=None) -> None:
    """Show a simple activity log viewer dialog."""
    from tkinter import Toplevel, Frame, Label, Button, StringVar, ttk
    from tkinter import messagebox
    from ui_theme import ModernButton
    from utils import C
    from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready

    win = Toplevel(parent)
    hide_while_building(win)
    win.title("Activity Log")
    win.geometry("900x600")
    win.transient(parent)
    win.configure(bg=C["bg"])

    # Filters
    filter_f = Frame(win, bg=C["bg"])
    filter_f.pack(fill="x", padx=12, pady=(8, 4))

    Label(filter_f, text="User:", bg=C["bg"], fg=C["muted"]).pack(side="left", padx=(0, 4))
    user_var = StringVar(value="")
    ttk.Combobox(filter_f, textvariable=user_var, width=15,
                 values=["", "owner", "manager", "staff"]).pack(side="left", padx=(0, 8))

    Label(filter_f, text="Event:", bg=C["bg"], fg=C["muted"]).pack(side="left", padx=(0, 4))
    event_var = StringVar(value="")
    ev_choices = sorted(evt for evt in EVENT_TYPES)
    ttk.Combobox(filter_f, textvariable=event_var, width=20,
                 values=[""] + ev_choices).pack(side="left", padx=(0, 8))

    Label(filter_f, text="Entity:", bg=C["bg"], fg=C["muted"]).pack(side="left", padx=(0, 4))
    entity_var = StringVar(value="")
    ttk.Combobox(filter_f, textvariable=entity_var, width=15,
                 values=["", "bill", "customer", "product", "backup", "settings"]).pack(side="left", padx=(0, 8))

    def _refresh():
        for row in tree.get_children():
            tree.delete(row)
        rows = query_events(
            limit=500,
            user_filter=user_var.get().strip(),
            event_filter=event_var.get().strip(),
            entity_filter=entity_var.get().strip(),
        )
        for r in rows:
            vals = [
                r.get("timestamp", ""),
                r.get("event", ""),
                r.get("entity", ""),
                r.get("entity_id", ""),
                r.get("user", ""),
                r.get("details", "")[:80],
            ]
            tree.insert("", "end", values=vals)

    ModernButton(filter_f, text="Refresh", command=_refresh,
                 color=C["blue"], hover_color="#154360",
                 width=80, height=26, radius=6,
                 font=("Arial", 9)).pack(side="left")

    # Treeview
    cols = ("timestamp", "event", "entity", "entity_id", "user", "details")
    headings = ("Time", "Event", "Entity", "ID", "User", "Details")
    widths = (150, 160, 90, 120, 80, 280)

    tree_f = Frame(win, bg=C["bg"])
    tree_f.pack(fill="both", expand=True, padx=12, pady=4)

    tree = ttk.Treeview(tree_f, columns=cols, show="headings", height=20)
    for col, hd, w in zip(cols, headings, widths):
        tree.heading(col, text=hd)
        tree.column(col, width=w, minwidth=50)
    tree.pack(side="left", fill="both", expand=True)

    vsb = ttk.Scrollbar(tree_f, orient="vertical", command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=vsb.set)

    # Detail label
    detail_var = StringVar(value="")
    detail_lbl = Label(win, textvariable=detail_var, bg=C["bg"], fg=C["muted"],
                       font=("Arial", 8), anchor="w", wraplength=860, justify="left")
    detail_lbl.pack(fill="x", padx=12, pady=(0, 4))

    def _on_select(_evt):
        sel = tree.selection()
        if not sel:
            detail_var.set("")
            return
        item = tree.item(sel[0])
        detail_var.set(f"Details: {item['values'][5]}")

    tree.bind("<<TreeviewSelect>>", _on_select)

    # Bottom bar
    bot_f = Frame(win, bg=C["bg"])
    bot_f.pack(fill="x", padx=12, pady=4)
    total = get_event_count()
    Label(bot_f, text=f"Total entries: {total}", bg=C["bg"],
          fg=C["muted"], font=("Arial", 9)).pack(side="left")

    def _purge_old():
        if messagebox.askyesno("Purge Old Logs",
                               "Delete logs older than 90 days?"):
            deleted = purge_older_than(90)
            messagebox.showinfo("Done", f"Deleted {deleted} old entries.")
            _refresh()

    ModernButton(bot_f, text="Purge >90 days", command=_purge_old,
                 color=C["orange"], hover_color="#93562B",
                 width=120, height=26, radius=6,
                 font=("Arial", 9)).pack(side="right")

    win.bind("<Configure>", lambda e: None)  # force layout
    _refresh()
    reveal_when_ready(win)
