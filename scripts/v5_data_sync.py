"""
v5_data_sync.py -- Correct Migration Script
Migrates data from kv_store JSON blobs to v5 structured SQLite tables.
Fixes: staff, customers, inventory all showing empty.
"""
import sys, os, json

sys.path.insert(0, r'g:\chimmu\Bobys_Salon Billing\B-Lite Billing manual edit')
os.chdir(r'g:\chimmu\Bobys_Salon Billing\B-Lite Billing manual edit')

from db import get_db

conn = get_db()

# --- 1. Migrate kv_store[staff] -> v5_staff ---
print("=== 1. Syncing Staff to v5 ===")
try:
    row = conn.execute("SELECT value FROM kv_store WHERE key='staff'").fetchone()
    if row:
        staff_data = json.loads(row["value"])
        print(f"  Found {len(staff_data)} staff in kv_store.")
        existing = {r["legacy_name"] for r in conn.execute("SELECT legacy_name FROM v5_staff").fetchall()}
        migrated = 0
        for name, s in staff_data.items():
            if name in existing:
                continue
            conn.execute(
                """
                INSERT INTO v5_staff(legacy_name, display_name, role_name, phone, commission_pct, salary, active, photo_path)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    name, name, s.get("role","staff"), s.get("phone",""),
                    float(s.get("commission_pct",0)), float(s.get("salary",0)),
                    1 if s.get("active",True) else 0, ""
                )
            )
            migrated += 1
        conn.commit()
        print(f"  [OK] Synced {migrated} staff to v5_staff.")
    else:
        print("  [INFO] No staff in kv_store.")
except Exception as e:
    print(f"  [ERROR] Staff: {e}")

# --- 2. Migrate kv_store[customers] -> v5_customers ---
print("\n=== 2. Syncing Customers to v5 ===")
try:
    row = conn.execute("SELECT value FROM kv_store WHERE key='customers'").fetchone()
    if row:
        cust_data = json.loads(row["value"])
        print(f"  Found {len(cust_data)} customers in kv_store.")
        existing = {r["legacy_phone"] for r in conn.execute("SELECT legacy_phone FROM v5_customers").fetchall()}
        migrated = 0
        for phone, c in cust_data.items():
            if phone in existing:
                continue
            conn.execute(
                """
                INSERT INTO v5_customers(legacy_phone, name, birthday, vip, points_balance)
                VALUES(?,?,?,?,?)
                """,
                (phone, c.get("name",""), c.get("birthday",""), 1 if c.get("vip",False) else 0, int(c.get("points",0)))
            )
            migrated += 1
        conn.commit()
        print(f"  [OK] Synced {migrated} customers to v5_customers.")
    else:
        print("  [INFO] No customers in kv_store.")
except Exception as e:
    print(f"  [ERROR] Customers: {e}")

# --- 3. Migrate kv_store[inventory] -> v5_inventory_items ---
print("\n=== 3. Syncing Inventory to v5 ===")
try:
    row = conn.execute("SELECT value FROM kv_store WHERE key='inventory'").fetchone()
    if row:
        inv_data = json.loads(row["value"])
        print(f"  Found {len(inv_data)} inventory items in kv_store.")
        existing = {r["legacy_name"] for r in conn.execute("SELECT legacy_name FROM v5_inventory_items").fetchall()}
        migrated = 0
        for name, item in inv_data.items():
            if name in existing:
                continue
            conn.execute(
                """
                INSERT INTO v5_inventory_items(legacy_name, category, brand, unit, current_qty, min_qty, cost_price, sale_price, active)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    name, item.get("category",""), item.get("brand",""), item.get("unit","pcs"),
                    float(item.get("qty",0)), float(item.get("min_stock",5)),
                    float(item.get("cost",0)), float(item.get("sell_price",0)), 1
                )
            )
            migrated += 1
        conn.commit()
        print(f"  [OK] Synced {migrated} items to v5_inventory_items.")
    else:
        print("  [INFO] No inventory in kv_store.")
except Exception as e:
    print(f"  [ERROR] Inventory: {e}")

# --- 4. Final Verification ---
print("\n=== Verification ===")
for table in ("v5_staff", "v5_customers", "v5_inventory_items"):
    count = conn.execute(f"SELECT COUNT(*) as n FROM {table}").fetchone()["n"]
    print(f"  {table}: {count} rows")
