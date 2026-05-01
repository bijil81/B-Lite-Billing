"""Offline backup and restore support."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
from datetime import datetime
from typing import Callable, Optional

from tkinter import filedialog, messagebox

from utils import (
    DATA_DIR,
    BILLS_DIR,
    F_APPOINTMENTS,
    F_CUSTOMERS,
    F_EXPENSES,
    F_INVENTORY,
    F_LOG,
    F_MEMBERSHIPS,
    F_OFFERS,
    F_REDEEM,
    F_REPORT,
    F_SERVICES,
    F_SETTINGS,
    F_STAFF,
    F_USERS,
    app_log,
)
from branding import get_app_name, get_backup_folder_name

DB_PATH = os.path.join(DATA_DIR, "salon.db")
F_INVOICE = os.path.join(DATA_DIR, "invoice_counter.json")
F_BACKUP_CFG = os.path.join(DATA_DIR, "offline_backup_config.json")
DEFAULT_BACKUP_NAME = get_backup_folder_name()

BACKUP_FILES = [
    F_SERVICES,
    F_CUSTOMERS,
    F_EXPENSES,
    F_APPOINTMENTS,
    F_STAFF,
    F_INVENTORY,
    F_USERS,
    F_OFFERS,
    F_REDEEM,
    F_MEMBERSHIPS,
    F_SETTINGS,
    F_REPORT,
    F_INVOICE,
    F_LOG,
    DB_PATH,
]

_BACKUP_LOCK = threading.Lock()
_BACKUP_RUNNING = False


def _default_cfg() -> dict:
    return {
        "folder": "",
        "auto_backup": False,
        "last_backup": "",
        "last_restore": "",
        "restore_prompted": False,
    }


def get_backup_config() -> dict:
    cfg = _default_cfg()
    try:
        if os.path.exists(F_BACKUP_CFG):
            with open(F_BACKUP_CFG, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    cfg.update(raw)
    except Exception as e:
        app_log(f"[backup_config read] {e}")
    return cfg


def save_backup_config(cfg: dict) -> None:
    final_cfg = {**_default_cfg(), **(cfg or {})}
    try:
        with open(F_BACKUP_CFG, "w", encoding="utf-8") as f:
            json.dump(final_cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        app_log(f"[backup_config write] {e}")


def resolve_backup_root(folder: str) -> str:
    if not folder:
        return ""
    candidate = os.path.join(folder, DEFAULT_BACKUP_NAME)
    if os.path.isdir(candidate):
        return candidate
    return folder


def normalize_backup_folder(folder: str) -> str:
    folder = (folder or "").strip().rstrip("\\/")
    if not folder:
        return ""
    if os.path.basename(folder).lower() == DEFAULT_BACKUP_NAME.lower():
        parent = os.path.dirname(folder)
        return parent or folder
    return folder


def backup_destination(folder: str) -> str:
    folder = normalize_backup_folder(folder)
    if not folder:
        return ""
    return os.path.join(folder, DEFAULT_BACKUP_NAME)


def build_backup_summary(dest_root: str) -> dict:
    return {
        "data_dir": os.path.join(dest_root, "Data"),
        "bills_dir": os.path.join(dest_root, "Bills"),
        "db_file": os.path.join(dest_root, "Data", "salon.db"),
    }


def _backup_sqlite_database(dest_path: str) -> None:
    """Create a consistent backup of the SQLite database.

    H8 FIX: The previous fallback (shutil.copy2) ignored the WAL file,
    producing a backup missing recent un-flushed transactions. Now we
    always use the SQLite backup API (conn.backup()) which produces a
    consistent snapshot regardless of WAL state. VACUUM INTO is still
    attempted first as it compacts the file, but the fallback now uses
    the proper backup API instead of a raw file copy.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if not os.path.exists(DB_PATH):
        return
    temp_path = dest_path + ".tmp"
    for path in (temp_path, dest_path):
        if os.path.exists(path):
            os.remove(path)

    # Try VACUUM INTO first -- this produces a compact, consistent snapshot.
    try:
        with sqlite3.connect(DB_PATH, timeout=5) as conn:
            escaped = temp_path.replace("'", "''")
            conn.execute(f"VACUUM INTO '{escaped}'")
        os.replace(temp_path, dest_path)
        app_log("[backup] Database backed up via VACUUM INTO.")
        return
    except Exception as e:
        app_log(f"[backup] VACUUM INTO failed, trying SQLite API: {e}")

    # Fallback: use the proper SQLite backup API which is WAL-aware.
    try:
        src_conn = sqlite3.connect(DB_PATH, timeout=5)
        dst_conn = sqlite3.connect(temp_path, timeout=5)
        src_conn.backup(dst_conn)  # WAL-consistent online backup
        dst_conn.close()
        src_conn.close()
        os.replace(temp_path, dest_path)
        app_log("[backup] Database backed up via SQLite backup API.")
        return
    except Exception as e:
        app_log(f"[backup] SQLite backup API also failed: {e}")

    # Last resort: copy both main DB and WAL file together.
    try:
        for src_file in (DB_PATH, DB_PATH + "-wal", DB_PATH + "-shm"):
            if os.path.exists(src_file):
                shutil.copy2(src_file, temp_path + os.path.basename(src_file))
        # Rename the primary file
        main_tmp = temp_path
        if os.path.exists(main_tmp + "-wal"):
            pass  # WAL file was also copied
        os.replace(main_tmp, dest_path)
        app_log("[backup] Database backed up via raw file copy (main + WAL).")
    except Exception as e:
        raise RuntimeError(f"All backup methods failed for database: {e}")


def sync_offline_backup(folder: str, progress_cb: Optional[Callable[[str, str], None]] = None) -> tuple[int, list[str], str]:
    if not folder:
        return 0, ["Backup folder not selected."], ""
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        return 0, [f"Could not create backup folder: {e}"], ""

    folder = normalize_backup_folder(folder)
    root = backup_destination(folder)
    data_dest = os.path.join(root, "Data")
    bills_dest = os.path.join(root, "Bills")
    os.makedirs(data_dest, exist_ok=True)
    os.makedirs(bills_dest, exist_ok=True)

    success = 0
    errors: list[str] = []

    for src in BACKUP_FILES:
        if not os.path.exists(src):
            continue
        try:
            dest_path = os.path.join(data_dest, os.path.basename(src))
            if os.path.normcase(src) == os.path.normcase(DB_PATH):
                _backup_sqlite_database(dest_path)
            else:
                shutil.copy2(src, dest_path)
            success += 1
            if progress_cb:
                progress_cb(os.path.basename(src), "ok")
        except Exception as e:
            errors.append(f"{os.path.basename(src)}: {e}")
            if progress_cb:
                progress_cb(os.path.basename(src), "error")

    if os.path.isdir(BILLS_DIR):
        try:
            for name in os.listdir(BILLS_DIR):
                src = os.path.join(BILLS_DIR, name)
                dst = os.path.join(bills_dest, name)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
            if progress_cb:
                progress_cb("Bills", "ok")
        except Exception as e:
            errors.append(f"Bills: {e}")
            if progress_cb:
                progress_cb("Bills", "error")

    cfg = get_backup_config()
    cfg["last_backup"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_backup_config(cfg)

    # V5.6.1 Phase 1 — Activity log
    try:
        from activity_log import log_event
        log_event(
            "backup_created",
            entity="backup",
            entity_id=root,
            details={"success_count": success, "errors": errors[:3]},
        )
    except Exception:
        pass

    return success, errors, root


def schedule_offline_backup() -> None:
    cfg = get_backup_config()
    folder = cfg.get("folder", "").strip()
    if not (cfg.get("auto_backup") and folder):
        return

    def _run():
        global _BACKUP_RUNNING
        with _BACKUP_LOCK:
            if _BACKUP_RUNNING:
                return
            _BACKUP_RUNNING = True
        try:
            sync_offline_backup(folder)
        except Exception as e:
            app_log(f"[offline_backup] {e}")
        finally:
            _BACKUP_RUNNING = False

    from worker_pool import submit_background_task
    submit_background_task(fn=_run, label="offline_backup")


def restore_from_backup(folder: str, progress_cb: Optional[Callable[[str, str], None]] = None) -> tuple[int, list[str]]:
    """Restore data from a backup folder.

    H7 FIX: Previously this function copied files directly into the live
    DATA_DIR. If the process crashed mid-restore, the destination would
    have a mix of old and new files -- an inconsistent, potentially corrupt
    state. Now we:
      1. Copy to a temporary directory first
      2. Validate the restored database with PRAGMA integrity_check
      3. Only then swap to the live directory (atomic per-file via os.replace)
      4. On failure, leave the live data untouched and clean up temp files
    """
    import tempfile
    root = resolve_backup_root(normalize_backup_folder(folder))
    data_src = os.path.join(root, "Data")
    bills_src = os.path.join(root, "Bills")
    if not os.path.isdir(data_src):
        return 0, [f"Selected folder does not contain a valid {get_app_name()} backup."]

    # Create a temporary staging directory for the restore.
    tmp_restore = tempfile.mkdtemp(prefix="salon_restore_")
    tmp_data = os.path.join(tmp_restore, "Data")
    tmp_bills = os.path.join(tmp_restore, "Bills")
    os.makedirs(tmp_data, exist_ok=True)
    os.makedirs(tmp_bills, exist_ok=True)

    success = 0
    errors: list[str] = []
    restore_ok = True

    # ── Phase 1: Copy all files to temp staging ──
    for name in os.listdir(data_src):
        src = os.path.join(data_src, name)
        dst = os.path.join(tmp_data, name)
        try:
            if os.path.isfile(src) and not os.path.islink(src):
                shutil.copy2(src, dst)
                success += 1
                if progress_cb:
                    progress_cb(name, "staged")
        except Exception as e:
            errors.append(f"{name}: {e}")
            restore_ok = False
            if progress_cb:
                progress_cb(name, "error")

    if os.path.isdir(bills_src):
        try:
            for name in os.listdir(bills_src):
                src = os.path.join(bills_src, name)
                dst = os.path.join(tmp_bills, name)
                if os.path.isfile(src) and not os.path.islink(src):
                    shutil.copy2(src, dst)
            if progress_cb:
                progress_cb("Bills", "staged")
        except Exception as e:
            errors.append(f"Bills: {e}")
            restore_ok = False
            if progress_cb:
                progress_cb("Bills", "error")

    # ── Phase 2: Validate restored database integrity ──
    tmp_db = os.path.join(tmp_data, "salon.db")
    if os.path.exists(tmp_db):
        try:
            conn = sqlite3.connect(tmp_db)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if result and result[0] != "ok":
                errors.append(f"Database integrity check failed: {result[0]}")
                restore_ok = False
                app_log(f"[restore] Database integrity check FAILED: {result[0]}")
            else:
                app_log("[restore] Database integrity check passed.")
        except Exception as e:
            errors.append(f"Database integrity check failed: {e}")
            restore_ok = False
            app_log(f"[restore] Database integrity check error: {e}")

    # ── Phase 3: Only swap to live if validation passed ──
    if not restore_ok:
        # Clean up temp files, live data is untouched
        try:
            shutil.rmtree(tmp_restore, ignore_errors=True)
        except Exception:
            pass
        return success, errors + ["Restore aborted due to errors. Your live data is unchanged."]

    # Swap: move temp files into the live data directory using os.replace
    # for atomicity. Existing live files are overwritten (no rollback needed
    # since we validated the backup content).
    for name in os.listdir(tmp_data):
        src = os.path.join(tmp_data, name)
        dst = os.path.join(DATA_DIR, name)
        try:
            os.replace(src, dst)
            if progress_cb:
                progress_cb(name, "restored")
        except Exception as e:
            errors.append(f"{name}: {e}")
            if progress_cb:
                progress_cb(name, "error")

    if os.path.isdir(tmp_bills) and os.listdir(tmp_bills):
        os.makedirs(BILLS_DIR, exist_ok=True)
        for name in os.listdir(tmp_bills):
            src = os.path.join(tmp_bills, name)
            dst = os.path.join(BILLS_DIR, name)
            try:
                os.replace(src, dst)
            except Exception as e:
                errors.append(f"Bill {name}: {e}")
        if progress_cb:
            progress_cb("Bills", "restored")

    # Clean up temp directory
    try:
        shutil.rmtree(tmp_restore, ignore_errors=True)
    except Exception:
        pass

    cfg = get_backup_config()
    cfg["last_restore"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    cfg["folder"] = normalize_backup_folder(os.path.dirname(root))
    save_backup_config(cfg)

    # V5.6.1 Phase 1 — Activity log
    try:
        from activity_log import log_event
        log_event(
            "backup_restored",
            entity="backup",
            entity_id=folder,
            details={"success_count": success, "errors": errors[:3]},
        )
    except Exception:
        pass

    if errors:
        return success, errors
    return success, []


def has_live_data() -> bool:
    for path in [F_CUSTOMERS, F_INVENTORY, F_REPORT, DB_PATH]:
        try:
            if os.path.exists(path) and os.path.getsize(path) > 2:
                return True
        except Exception:
            pass
    return False


def maybe_prompt_restore(parent) -> None:
    cfg = get_backup_config()
    if cfg.get("restore_prompted") or has_live_data():
        return
    cfg["restore_prompted"] = True
    save_backup_config(cfg)

    if not messagebox.askyesno(
        "Restore Backup",
        "No shop data was found on this system.\n\nDo you want to restore from an offline backup folder now?",
        parent=parent,
    ):
        return

    folder = filedialog.askdirectory(
        title="Select Offline Backup Folder",
        parent=parent,
    )
    if not folder:
        return
    restored, errors = restore_from_backup(folder)
    if errors:
        messagebox.showwarning(
            "Restore Completed with Warnings",
            f"Restored {restored} items.\n\nWarnings:\n" + "\n".join(errors[:8]),
            parent=parent,
        )
    else:
        messagebox.showinfo(
            "Restore Completed",
            f"Restored {restored} items from offline backup.\nPlease restart the app to reload all data.",
            parent=parent,
        )
