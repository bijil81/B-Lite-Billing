"""
kv_to_v5_migration.py -- One-time migration script
Migrates data from kv_store JSON blobs to v5 structured SQLite tables.
Fixes: staff, customers, inventory all showing empty.
Also: clears auth lockouts and resets login failures.
"""
import sys, os, json, time

sys.path.insert(0, r'g:\chimmu\Bobys_Salon Billing\B-Lite Billing manual edit')
os.chdir(r'g:\chimmu\Bobys_Salon Billing\B-Lite Billing manual edit')

from db import get_db

conn = get_db()

# --- 0. Check and clear auth lockouts ---
print("=== Step 0: Auth Lockout Check ===")
try:
    rows = conn.execute("SELECT username, locked_until FROM auth_lockouts").fetchall()
    now = time.time()
    for r in rows:
        locked = float(r["locked_until"] or 0) > now
        print("  user=%s  locked=%s  locked_until=%s" % (r["username"], locked, r["locked_until"]))
    conn.execute("DELETE FROM auth_lockouts")
    conn.commit()
    print("  [OK] All lockouts cleared.")
except Exception as e:
    print("  [INFO] auth_lockouts: %s" % e)

# --- 1. Migrate kv_store[staff] -> staff table ---
print()
print("=== Step 1: Staff Migration ===")
try:
    row = conn.execute("SELECT value FROM kv_store WHERE key='staff'").fetchone()
    if row:
        staff_data = json.loads(row["value"])
        print("  Found %d staff in kv_store." % len(staff_data))
        existing = {r["name"] for r in conn.execute("SELECT name FROM staff").fetchall()}
        print("  Existing in staff table: %d" % len(existing))
        migrated = 0
        for name, s in staff_data.items():
            if name in existing:
                print("    SKIP: %s" % name)
                continue
            conn.execute(
                "INSERT INTO staff(name, role, phone, commission_pct, salary, join_date, active, attendance, sales) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    name, s.get("role",""), s.get("phone",""),
                    float(s.get("commission_pct",0)), float(s.get("salary",0)),
                    s.get("join_date",""), 1 if s.get("active",True) else 0,
                    json.dumps(s.get("attendance",[])), json.dumps(s.get("sales",[])),
                )
            )
            migrated += 1
            print("    MIGRATED: %s" % name)
        conn.commit()
        print("  Staff done: %d inserted." % migrated)
    else:
        print("  [INFO] No staff in kv_store.")
except Exception as e:
    print("  [ERROR] Staff: %s" % e)

# --- 2. Migrate kv_store[customers] -> customers table ---
print()
print("=== Step 2: Customers Migration ===")
try:
    row = conn.execute("SELECT value FROM kv_store WHERE key='customers'").fetchone()
    if row:
        cust_data = json.loads(row["value"])
        print("  Found %d customers in kv_store." % len(cust_data))
        existing = {r["phone"] for r in conn.execute("SELECT phone FROM customers").fetchall()}
        migrated = 0
        for phone, c in cust_data.items():
            if phone in existing:
                continue
            conn.execute(
                "INSERT INTO customers(phone, name, birthday, points, visits, vip) VALUES(?,?,?,?,?,?)",
                (phone, c.get("name",""), c.get("birthday",""),
                 int(c.get("points",0)), json.dumps(c.get("visits",[])),
                 1 if c.get("vip",False) else 0)
            )
            migrated += 1
        conn.commit()
        print("  Customers done: %d inserted." % migrated)
    else:
        print("  [INFO] No customers in kv_store.")
except Exception as e:
    print("  [ERROR] Customers: %s" % e)

# --- 3. Migrate kv_store[inventory] -> inventory table ---
print()
print("=== Step 3: Inventory Migration ===")
try:
    row = conn.execute("SELECT value FROM kv_store WHERE key='inventory'").fetchone()
    if row:
        inv_data = json.loads(row["value"])
        print("  Found %d inventory items in kv_store." % len(inv_data))
        existing = {r["name"] for r in conn.execute("SELECT name FROM inventory").fetchall()}
        migrated = 0
        for name, item in inv_data.items():
            if name in existing:
                continue
            conn.execute(
                "INSERT INTO inventory(name, category, qty, unit, min_stock, cost, sell_price) VALUES(?,?,?,?,?,?,?)",
                (name, item.get("category",""), int(item.get("qty",0)),
                 item.get("unit","pcs"), int(item.get("min_stock",5)),
                 float(item.get("cost",0)), float(item.get("sell_price",0)))
            )
            migrated += 1
        conn.commit()
        print("  Inventory done: %d inserted." % migrated)
    else:
        print("  [INFO] No inventory in kv_store.")
except Exception as e:
    print("  [ERROR] Inventory: %s" % e)

# --- 4. Final Verification ---
print()
print("=== Step 4: Verification ===")
for table in ("staff", "customers", "inventory"):
    count = conn.execute("SELECT COUNT(*) as n FROM %s" % table).fetchone()["n"]
    print("  %s table: %d rows" % (table, count))

row = conn.execute("SELECT value FROM kv_store WHERE key='users'").fetchone()
users = json.loads(row["value"]) if row else {}
print("  kv_store[users]: %s" % list(users.keys()))

print()
print("[DONE] Migration complete. Restart the app.")
