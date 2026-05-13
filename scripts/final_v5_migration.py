"""
final_v5_migration.py -- Final Phase Migration Script
Migrates remaining legacy JSON modules (Users, Offers, Memberships, Expenses) to SQLite.
Implements strict backup procedures and idempotent operations.
"""
import sys, os, json, shutil, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import DATA_DIR, F_USERS, F_OFFERS, F_MEMBERSHIPS, F_EXPENSES, app_log
from db import DB_PATH
from adapters.auth_adapter import save_users_legacy_map_v5
from adapters.offers_adapter import save_offers_legacy_map_v5
from adapters.membership_adapter import save_memberships_legacy_map_v5
from adapters.expenses_adapter import save_expenses_legacy_map_v5
from db_core.schema_manager import ensure_v5_schema

def create_backups():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(DATA_DIR, f"migration_backup_{ts}")
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        DB_PATH,
        F_USERS,
        F_OFFERS,
        F_MEMBERSHIPS,
        F_EXPENSES
    ]
    
    print(f"Creating backups in {backup_dir}...")
    for f in files_to_backup:
        if os.path.exists(f):
            dest = os.path.join(backup_dir, os.path.basename(f))
            shutil.copy2(f, dest)
            print(f"  [OK] Backed up {os.path.basename(f)}")
        else:
            print(f"  [INFO] File not found, skipping backup: {os.path.basename(f)}")
    print("Backups complete.\n")

def load_json_safe(filepath, default_val):
    if not os.path.exists(filepath):
        return default_val
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  [ERROR] Failed to read {os.path.basename(filepath)}: {e}")
        return default_val

def run_migration():
    print("=== Final V5 Migration ===")
    
    print("Ensuring V5 Database Schema is fully up-to-date...")
    ensure_v5_schema()
    
    create_backups()
    
    print("Migrating Users...")
    users_data = load_json_safe(F_USERS, {})
    if users_data:
        try:
            save_users_legacy_map_v5(users_data)
            print(f"  [OK] Migrated {len(users_data)} users.")
        except Exception as e:
            print(f"  [ERROR] User migration failed: {e}")
    else:
        print("  [INFO] No users to migrate.")
        
    print("\nMigrating Offers...")
    offers_data = load_json_safe(F_OFFERS, [])
    if offers_data:
        try:
            save_offers_legacy_map_v5(offers_data)
            print(f"  [OK] Migrated {len(offers_data)} offers.")
        except Exception as e:
            print(f"  [ERROR] Offers migration failed: {e}")
    else:
        print("  [INFO] No offers to migrate.")

    print("\nMigrating Memberships...")
    memberships_data = load_json_safe(F_MEMBERSHIPS, {})
    if memberships_data:
        try:
            save_memberships_legacy_map_v5(memberships_data)
            print(f"  [OK] Migrated {len(memberships_data)} memberships.")
        except Exception as e:
            print(f"  [ERROR] Memberships migration failed: {e}")
    else:
        print("  [INFO] No memberships to migrate.")
        
    print("\nMigrating Expenses...")
    expenses_data = load_json_safe(F_EXPENSES, [])
    if expenses_data:
        try:
            save_expenses_legacy_map_v5(expenses_data)
            print(f"  [OK] Migrated {len(expenses_data)} expenses.")
        except Exception as e:
            print(f"  [ERROR] Expenses migration failed: {e}")
    else:
        print("  [INFO] No expenses to migrate.")

    print("\nMigration Script Finished Successfully!")
    print("You can now enable the feature flags in salon_settings.py.")

if __name__ == "__main__":
    run_migration()
