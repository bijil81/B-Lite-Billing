"""
db.py  –  BOBY'S Salon : SQLite Database Layer  v1.0
Dual-Mode Migration — SQLite primary, JSON backup.

Architecture:
  - db_load(path)       : replaces load_json()  — reads SQLite first, JSON fallback
  - db_save(path, data) : replaces save_json()  — writes SQLite + JSON backup atomically
  - migrate_from_json() : one-time import of all existing JSON → SQLite
  - rollback_to_json()  : emergency export — SQLite → JSON files (full rollback)
  - get_db()            : thread-safe SQLite connection
  - ensure_migrated()   : call from main.py on startup

Transparent to existing code — only utils.py load_json/save_json need swapping.
JSON files kept as backup after migration. Never deleted automatically.
"""

import os, json, sqlite3, shutil, threading
from datetime import datetime
from branding import get_appdata_dir_name


# ─────────────────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────────────────

def _get_data_dir() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    root = os.path.join(base, get_appdata_dir_name())
    os.makedirs(root, exist_ok=True)
    return root


DATA_DIR = _get_data_dir()
DB_PATH  = os.path.join(DATA_DIR, "salon.db")

# JSON path → logical SQLite key mapping
_JSON_TO_KEY = {
    os.path.join(DATA_DIR, "customers.json"):       "customers",
    os.path.join(DATA_DIR, "appointments.json"):    "appointments",
    os.path.join(DATA_DIR, "expenses.json"):        "expenses",
    os.path.join(DATA_DIR, "inventory.json"):       "inventory",
    os.path.join(DATA_DIR, "staff.json"):           "staff",
    os.path.join(DATA_DIR, "services_db.json"):     "services_db",
    os.path.join(DATA_DIR, "memberships.json"):     "memberships",
    os.path.join(DATA_DIR, "offers.json"):          "offers",
    os.path.join(DATA_DIR, "redeem_codes.json"):    "redeem_codes",
    os.path.join(DATA_DIR, "users.json"):           "users",
    os.path.join(DATA_DIR, "salon_settings.json"):  "settings",
    os.path.join(DATA_DIR, "invoice_counter.json"): "invoice_counter",
    os.path.join(DATA_DIR, "pkg_templates.json"):   "pkg_templates",
}


# ─────────────────────────────────────────────────────────
#  CONNECTION  (thread-local, WAL mode)
# ─────────────────────────────────────────────────────────

_local = threading.local()


def get_db() -> sqlite3.Connection:
    """Thread-safe connection. Creates DB + schema on first call."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = _open_connection()
    try:
        _local.conn.execute("SELECT 1")
    except Exception:
        _local.conn = _open_connection()
    return _local.conn


def _open_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    _create_schema(conn)
    return conn


def close_db():
    if hasattr(_local, "conn") and _local.conn:
        try:
            _local.conn.close()
        except Exception as e:
            try:
                from utils import app_log
                app_log(f"[db close] {e}")
            except Exception:
                pass
        _local.conn = None


# ─────────────────────────────────────────────────────────
#  SCHEMA  (12 tables + universal kv_store)
# ─────────────────────────────────────────────────────────

def _create_schema(conn: sqlite3.Connection):
    conn.executescript("""
        -- Universal JSON adapter (one row per file)
        CREATE TABLE IF NOT EXISTS kv_store (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL DEFAULT '{}',
            updated TEXT DEFAULT (datetime('now'))
        );

        -- Customers
        CREATE TABLE IF NOT EXISTS customers (
            phone    TEXT PRIMARY KEY,
            name     TEXT NOT NULL DEFAULT '',
            birthday TEXT DEFAULT '',
            points   INTEGER DEFAULT 0,
            visits   TEXT    DEFAULT '[]',
            vip      INTEGER DEFAULT 0,
            created  TEXT    DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cust_name ON customers(name);

        -- Appointments
        CREATE TABLE IF NOT EXISTS appointments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            customer      TEXT DEFAULT '',
            phone         TEXT DEFAULT '',
            service       TEXT DEFAULT '',
            date          TEXT NOT NULL,
            time          TEXT DEFAULT '',
            staff         TEXT DEFAULT '',
            status        TEXT DEFAULT 'Scheduled'
                             CHECK(status IN ('Scheduled','Completed','Cancelled','No-Show','In-Progress')),
            created       TEXT DEFAULT (datetime('now')),
            dont_show     INTEGER DEFAULT 0,
            last_reminded TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_appt_date  ON appointments(date);
        CREATE INDEX IF NOT EXISTS idx_appt_phone ON appointments(phone);

        -- Booking calendar
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            service TEXT NOT NULL DEFAULT '',
            staff TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'booked'
                     CHECK(status IN ('booked','cancelled','completed','no-show')),
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_booking_date ON bookings(date);
        CREATE INDEX IF NOT EXISTS idx_booking_staff_date ON bookings(staff, date);

        -- Expenses
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            category    TEXT DEFAULT '',
            staff       TEXT DEFAULT '',
            description TEXT DEFAULT '',
            amount      REAL DEFAULT 0.0 CHECK(amount >= 0),
            added       TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_exp_date ON expenses(date);
        CREATE INDEX IF NOT EXISTS idx_exp_cat  ON expenses(category);

        -- Inventory
        CREATE TABLE IF NOT EXISTS inventory (
            name       TEXT PRIMARY KEY,
            category   TEXT DEFAULT '',
            qty        INTEGER DEFAULT 0 CHECK(qty >= 0),
            unit       TEXT DEFAULT 'pcs',
            min_stock  INTEGER DEFAULT 5,
            cost       REAL DEFAULT 0.0 CHECK(cost >= 0),
            sell_price REAL DEFAULT 0.0 CHECK(sell_price >= 0),
            updated    TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_inv_cat ON inventory(category);

        -- Staff
        CREATE TABLE IF NOT EXISTS staff (
            name           TEXT PRIMARY KEY,
            role           TEXT DEFAULT '',
            phone          TEXT DEFAULT '',
            commission_pct REAL DEFAULT 0.0 CHECK(commission_pct >= 0 AND commission_pct <= 100),
            salary         REAL DEFAULT 0.0 CHECK(salary >= 0),
            join_date      TEXT DEFAULT '',
            active         INTEGER DEFAULT 1,
            attendance     TEXT DEFAULT '[]',
            sales          TEXT DEFAULT '[]'
        );

        -- Services/Products catalogue
        CREATE TABLE IF NOT EXISTS services_db (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '{}'
        );

        -- Sales report (mirrors CSV)
        CREATE TABLE IF NOT EXISTS sales_report (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            date      TEXT NOT NULL,
            invoice   TEXT DEFAULT '',
            name      TEXT DEFAULT '',
            phone     TEXT DEFAULT '',
            payment   TEXT DEFAULT 'Cash',
            total     REAL DEFAULT 0.0 CHECK(total >= 0),
            discount  REAL DEFAULT 0.0 CHECK(discount >= 0),
            items_raw TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_sale_date    ON sales_report(date);
        CREATE INDEX IF NOT EXISTS idx_sale_invoice ON sales_report(invoice);
        CREATE INDEX IF NOT EXISTS idx_sale_phone   ON sales_report(phone);

        -- Memberships
        CREATE TABLE IF NOT EXISTS memberships (
            phone        TEXT PRIMARY KEY,
            package_name TEXT DEFAULT '',
            start_date   TEXT DEFAULT '',
            end_date     TEXT DEFAULT '',
            discount_pct REAL DEFAULT 0.0 CHECK(discount_pct >= 0 AND discount_pct <= 100),
            wallet       REAL DEFAULT 0.0 CHECK(wallet >= 0),
            status       TEXT DEFAULT 'Active'
                             CHECK(status IN ('Active','Expired','Cancelled','Suspended')),
            created      TEXT DEFAULT (datetime('now'))
        );

        -- Offers
        CREATE TABLE IF NOT EXISTS offers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT DEFAULT '',
            type         TEXT DEFAULT 'percentage',
            value        REAL DEFAULT 0.0,
            service_name TEXT DEFAULT '',
            coupon_code  TEXT DEFAULT '',
            valid_from   TEXT DEFAULT '',
            valid_to     TEXT DEFAULT '',
            description  TEXT DEFAULT '',
            active       INTEGER DEFAULT 1,
            created      TEXT DEFAULT (datetime('now'))
        );

        -- Redeem codes
        CREATE TABLE IF NOT EXISTS redeem_codes (
            code          TEXT PRIMARY KEY,
            discount_type TEXT DEFAULT 'flat',
            value         REAL DEFAULT 0.0,
            phone         TEXT DEFAULT '',
            name          TEXT DEFAULT '',
            expiry        TEXT DEFAULT '',
            note          TEXT DEFAULT '',
            used          INTEGER DEFAULT 0,
            used_on       TEXT DEFAULT '',
            used_invoice  TEXT DEFAULT '',
            created       TEXT DEFAULT (datetime('now'))
        );

        -- Users
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role     TEXT DEFAULT 'staff',
            name     TEXT DEFAULT '',
            active   INTEGER DEFAULT 1
        );

        -- Settings key-value
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        );
    """)
    conn.commit()


# ─────────────────────────────────────────────────────────
#  REFERENTIAL VALIDATION HELPERS (application-layer FK)
#
#  C4 FIX: We cannot add FOREIGN KEY constraints to existing
#  production databases without a migration. Instead we provide
#  validation helpers that the service layer SHOULD call before
#  inserting records that reference other entities.  These are
#  logged warnings when validation fails, allowing stale data to
#  be caught early without breaking existing callers.
# ─────────────────────────────────────────────────────────

def validate_customer_exists(phone: str, log_prefix: str = "refcheck") -> bool:
    """Return True if a customer with the given phone exists in the DB.

    Use this before inserting into appointments, bookings, memberships,
    redeem_codes, etc. to prevent orphan records.
    """
    if not phone or not phone.strip():
        return True  # allow empty phone (legacy behavior)
    try:
        row = get_db().execute(
            "SELECT 1 FROM customers WHERE phone = ?", (phone.strip(),)
        ).fetchone()
        return row is not None
    except Exception as e:
        from utils import app_log
        app_log(f"[{log_prefix}] customer lookup failed for {phone}: {e}")
        return True  # on DB error, don't block the operation


def warn_orphan_reference(table: str, field: str, value: str, log_prefix: str = "refcheck"):
    """Log a warning if a referenced entity does not exist.

    Use this AFTER an insert when the validation was not possible.
    """
    from utils import app_log
    app_log(f"[{log_prefix}] ORPHAN REFERENCE: {table}.{field}='{value}' "
            f"does not point to an existing entity. "
            f"Consider adding validation at the call site.")


# ─────────────────────────────────────────────────────────
#  DUAL-MODE LOAD / SAVE
# ─────────────────────────────────────────────────────────

def db_load(path: str, default=None):
    """
    Drop-in for load_json().
    1. Read from SQLite kv_store (fast)
    2. Fallback to JSON file if not in DB
    3. Return default if both fail
    """
    if default is None:
        default = {}

    def _normalize_payload(data):
        try:
            expected_type = type(default)
            if isinstance(default, (dict, list)) and not isinstance(data, expected_type):
                _db_log(
                    f"[db_load] Type mismatch for {path}: expected "
                    f"{expected_type.__name__}, got {type(data).__name__}. Using default.",
                    "warning",
                )
                return default
        except Exception:
            pass
        return data

    key = _JSON_TO_KEY.get(path)
    if key:
        try:
            row = get_db().execute(
                "SELECT value FROM kv_store WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return _normalize_payload(json.loads(row["value"]))
        except Exception as e:
            _db_log(f"[db_load] SQLite read failed for {key}: {e}")
    # Fallback: JSON file
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return _normalize_payload(json.load(f))
    except Exception as e:
        _db_log(f"[db_load] JSON fallback failed for {path}: {e}")
    return default


def db_save(path: str, data) -> bool:
    """
    Drop-in for save_json().
    Writes SQLite (primary) + JSON backup (atomic).
    Returns True if at least one write succeeded.
    """
    key       = _JSON_TO_KEY.get(path)
    sqlite_ok = False
    json_ok   = False

    # SQLite write
    if key:
        try:
            serialised = json.dumps(data, ensure_ascii=False)
            conn = get_db()
            conn.execute("""
                INSERT INTO kv_store (key, value, updated)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value   = excluded.value,
                    updated = excluded.updated
            """, (key, serialised))
            conn.commit()
            sqlite_ok = True
        except Exception as e:
            _db_log(f"[db_save] SQLite write failed for {key}: {e}")

    # JSON backup (atomic)
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        if os.path.exists(path):
            os.replace(tmp, path)
        else:
            os.rename(tmp, path)
        json_ok = True
    except Exception as e:
        _db_log(f"[db_save] JSON backup failed for {path}: {e}")
        try:
            if os.path.exists(path + ".tmp"):
                os.remove(path + ".tmp")
        except Exception:
            pass

    return sqlite_ok or json_ok


# ─────────────────────────────────────────────────────────
#  MIGRATION  (JSON → SQLite, one-time)
# ─────────────────────────────────────────────────────────

def migrate_from_json(data_dir: str = None) -> dict:
    """
    Import all existing JSON files into SQLite kv_store.
    Safe to call multiple times — uses INSERT OR REPLACE.
    Returns {"migrated": [...], "skipped": [...], "errors": [...]}
    """
    d        = data_dir or DATA_DIR
    migrated = []
    skipped  = []
    errors   = []

    for json_path, key in _JSON_TO_KEY.items():
        actual = os.path.join(d, os.path.basename(json_path))
        if not os.path.exists(actual):
            skipped.append(key)
            continue
        try:
            with open(actual, "r", encoding="utf-8") as f:
                data = json.load(f)
            conn = get_db()
            conn.execute("""
                INSERT INTO kv_store (key, value, updated)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value   = excluded.value,
                    updated = excluded.updated
            """, (key, json.dumps(data, ensure_ascii=False)))
            conn.commit()
            migrated.append(key)
            _db_log(f"[migrate] OK: {key}", "info")
        except Exception as e:
            errors.append(f"{key}: {e}")
            _db_log(f"[migrate] FAIL: {key}: {e}")

    _db_log(f"[migrate] Done — {len(migrated)} migrated, "
            f"{len(skipped)} skipped, {len(errors)} errors", "info")
    return {"migrated": migrated, "skipped": skipped, "errors": errors}


# ─────────────────────────────────────────────────────────
#  ROLLBACK  (SQLite → JSON)
# ─────────────────────────────────────────────────────────

def rollback_to_json(data_dir: str = None, backup_suffix: str = None) -> dict:
    """
    Emergency rollback — export kv_store back to JSON files.
    Existing JSON backed up with timestamp before overwrite.
    Returns {"exported": [...], "skipped": [...], "errors": [...]}
    """
    d        = data_dir or DATA_DIR
    suffix   = backup_suffix or datetime.now().strftime("_%Y%m%d_%H%M%S")
    exported = []
    skipped  = []
    errors   = []

    try:
        rows = get_db().execute(
            "SELECT key, value FROM kv_store"
        ).fetchall()
    except Exception as e:
        return {"exported": [], "skipped": [], "errors": [str(e)]}

    key_to_path = {v: k for k, v in _JSON_TO_KEY.items()}

    for row in rows:
        key  = row["key"]
        path = key_to_path.get(key)
        if not path:
            skipped.append(key)
            continue
        actual = os.path.join(d, os.path.basename(path))
        try:
            if os.path.exists(actual):
                shutil.copy2(actual, actual + suffix + ".bak")
            data = json.loads(row["value"])
            tmp  = actual + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(tmp, actual)
            exported.append(key)
            _db_log(f"[rollback] OK: {key}", "info")
        except Exception as e:
            errors.append(f"{key}: {e}")
            _db_log(f"[rollback] FAIL: {key}: {e}")

    _db_log(f"[rollback] Done — {len(exported)} exported, "
            f"{len(skipped)} skipped, {len(errors)} errors", "info")
    return {"exported": exported, "skipped": skipped, "errors": errors}


# ─────────────────────────────────────────────────────────
#  STATUS / BACKUP / HEALTH
# ─────────────────────────────────────────────────────────

def db_status() -> dict:
    """Return DB health info — useful for Settings screen."""
    try:
        conn     = get_db()
        tables   = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        kv_count = conn.execute(
            "SELECT COUNT(*) AS n FROM kv_store"
        ).fetchone()["n"]
        size     = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        return {
            "ok":      True,
            "db_path": DB_PATH,
            "tables":  [t["name"] for t in tables],
            "kv_keys": kv_count,
            "size_kb": round(size / 1024, 1),
            "size_mb": round(size / 1024 / 1024, 3),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def db_backup(backup_dir: str = None) -> str:
    """Create timestamped salon.db backup. Returns backup path."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found: {DB_PATH}")
    bdir = backup_dir or os.path.join(DATA_DIR, "Backups")
    os.makedirs(bdir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(bdir, f"salon_{ts}.db")
    try:
        bkp_conn = sqlite3.connect(dest)
        get_db().backup(bkp_conn)
        bkp_conn.close()
    except Exception:
        shutil.copy2(DB_PATH, dest)
    _db_log(f"[db_backup] Backed up to {dest}", "info")
    return dest


def ensure_migrated():
    """
    Call from main.py at startup.
    Auto-migrates JSON → SQLite on first run only.
    """
    try:
        kv_count = get_db().execute(
            "SELECT COUNT(*) AS n FROM kv_store"
        ).fetchone()["n"]
        if kv_count == 0:
            _db_log("[ensure_migrated] First run — migrating JSON files...", "info")
            result = migrate_from_json()
            _db_log(f"[ensure_migrated] Done: {len(result['migrated'])} files.", "info")
        else:
            _db_log(f"[ensure_migrated] DB ready ({kv_count} keys).", "info")
    except Exception as e:
        _db_log(f"[ensure_migrated] {e}")


# ─────────────────────────────────────────────────────────
#  INTERNAL LOGGER
# ─────────────────────────────────────────────────────────

def _db_log(msg: str, level: str = "error"):
    try:
        from utils import app_log
        app_log(msg, level)
    except Exception:
        print(msg)


# ─────────────────────────────────────────────────────────
#  SELF-TEST  (python db.py)
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== BOBY's Salon DB Layer — Self Test ===\n")
    s = db_status()
    print(f"DB Path : {s.get('db_path')}")
    print(f"Tables  : {s.get('tables')}")
    print(f"KV Keys : {s.get('kv_keys')}")
    print(f"Size    : {s.get('size_kb')} KB\n")

    from utils import DATA_DIR as _D, F_SETTINGS
    test_data = {"salon_name": "BOBY'S BEAUTY SALON", "test": True}
    ok = db_save(F_SETTINGS, test_data)
    print(f"db_save  : {'OK' if ok else 'FAILED'}")
    loaded = db_load(F_SETTINGS, {})
    print(f"db_load  : {'OK' if loaded.get('test') else 'FAILED'} → {loaded}\n")

    print("migrate_from_json()...")
    r = migrate_from_json()
    print(f"  migrated={r['migrated']}")
    print(f"  skipped ={r['skipped']}")
    print(f"  errors  ={r['errors']}\n")

    s2 = db_status()
    print(f"KV keys after: {s2['kv_keys']}, Size: {s2['size_kb']} KB")

    print("\nrollback_to_json()...")
    rb = rollback_to_json()
    print(f"  exported={rb['exported']}")
    print(f"  errors  ={rb['errors']}")
    print("\n=== Self Test Complete ===")
