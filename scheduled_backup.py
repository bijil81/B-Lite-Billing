"""Scheduled backup — daily/weekly auto-backup with retention.

Extends backup_system.py with:
  - Daily or weekly schedule
  - Configurable backup time
  - Configurable retention count (keep latest N)
  - Background execution via worker_pool
  - Does NOT break existing manual backup flow

Created for V5.6.1 Phase 1 — Safety & Recovery.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Callable, Optional

from backup_system import (
    normalize_backup_folder,
    backup_destination,
    sync_offline_backup,
    get_backup_config,
    save_backup_config,
)
from branding import get_backup_folder_name
from utils import app_log, DATA_DIR

# Config file extends the existing offline_backup_config.json
_F_SCHED_CFG = os.path.join(DATA_DIR, "scheduled_backup_config.json")

_DEFAULT_FREQ = "daily"       # "daily" | "weekly"
_DEFAULT_TIME = "02:00"       # 24h format
_DEFAULT_RETENTION = 7        # keep latest N
_DEFAULT_WEEKDAY = "monday"   # for weekly schedule

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

_SCHED_LOCK = threading.Lock()


def _default_sched_cfg() -> dict:
    return {
        "enabled": False,
        "frequency": _DEFAULT_FREQ,
        "time": _DEFAULT_TIME,
        "retention": _DEFAULT_RETENTION,
        "weekday": _DEFAULT_WEEKDAY,
        "last_backup": "",
        "last_error": "",
    }


def get_scheduled_config() -> dict:
    """Return merged scheduled backup config."""
    cfg = _default_sched_cfg()
    try:
        if os.path.exists(_F_SCHED_CFG):
            with open(_F_SCHED_CFG, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    cfg.update(raw)
    except Exception as e:
        app_log(f"[sched_backup config read] {e}")
    return cfg


def save_scheduled_config(cfg: dict) -> bool:
    """Persist scheduled backup config. Merges with defaults."""
    final = {**_default_sched_cfg(), **(cfg or {})}
    try:
        with open(_F_SCHED_CFG, "w", encoding="utf-8") as f:
            json.dump(final, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        app_log(f"[sched_backup config write] {e}")
        return False


def run_scheduled_backup(progress_cb: Optional[Callable] = None) -> tuple[int, list[str], str]:
    """Execute a scheduled backup and enforce retention.

    Uses backup_system.sync_offline_backup() underneath — same
    data, same consistency, only the trigger is different.
    """
    with _SCHED_LOCK:
        sched_cfg = get_scheduled_config()
        base_cfg = get_backup_config()
        folder = base_cfg.get("folder", "").strip()
        if not folder:
            app_log("[sched_backup] No backup folder configured.")
            return 0, ["No backup folder configured."], ""

        folder = normalize_backup_folder(folder)
        root = backup_destination(folder)

        # Add timestamp suffix to backup folder name so each run
        # creates a unique snapshot directory.
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{get_backup_folder_name()}_{ts}"
        dest_root = os.path.join(folder, backup_name)
        os.makedirs(dest_root, exist_ok=True)

        # Run the actual backup
        success, errors, _ignored = sync_offline_backup(dest_root, progress_cb=progress_cb)

        # Update last_backup timestamps
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        sched_cfg["last_backup"] = now_str
        if errors:
            sched_cfg["last_error"] = errors[0][:200]
        else:
            sched_cfg["last_error"] = ""
        save_scheduled_config(sched_cfg)

        base_cfg["last_backup"] = now_str
        save_backup_config(base_cfg)

        # Activity log hook
        try:
            from activity_log import log_event
            log_event(
                "backup_created",
                entity="backup",
                entity_id=backup_name,
                details={"destination": dest_root, "success_count": success, "errors": errors},
            )
        except Exception:
            pass

        # Enforce retention — keep only latest N backups
        if success > 0:
            _enforce_retention(folder, sched_cfg.get("retention", _DEFAULT_RETENTION), backup_name)

        return success, errors, dest_root


def _enforce_retention(root_folder: str, keep: int, latest_name: str) -> None:
    """Delete oldest backup folders, keep only the latest N."""
    try:
        prefix = get_backup_folder_name()
        entries = []
        for name in os.listdir(root_folder):
            if name.startswith(prefix) and os.path.isdir(os.path.join(root_folder, name)):
                entries.append(name)

        if len(entries) <= keep:
            return

        # Sort by name (contains timestamp), newest first
        entries.sort(reverse=True)

        # Always keep the latest backup even if retention is 0
        to_delete = entries[keep:]
        if latest_name in to_delete:
            to_delete.remove(latest_name)

        import shutil
        for name in to_delete:
            path = os.path.join(root_folder, name)
            try:
                shutil.rmtree(path)
                app_log(f"[sched_backup.retention] Deleted old backup: {name}")
            except Exception as e:
                app_log(f"[sched_backup.retention] Failed to delete {name}: {e}")
    except Exception as e:
        app_log(f"[sched_backup.retention] {e}")


# ── Scheduler Loop ──────────────────────────────────────────

_scheduler_thread: Optional[threading.Thread] = None
_scheduler_stop = threading.Event()


def _validate_time(t: str) -> bool:
    """Check HH:MM format."""
    try:
        parts = t.split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        return False


def get_next_backup_time() -> datetime:
    """Compute the next datetime when backup should run."""
    cfg = get_scheduled_config()
    frequency = cfg.get("frequency", "daily")
    time_str = cfg.get("time", "02:00")
    weekday = cfg.get("weekday", "monday")

    if not _validate_time(time_str):
        time_str = "02:00"

    h, m = map(int, time_str.split(":"))
    now = datetime.now()
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)

    if target <= now:
        target = target.replace(day=target.day + 1)

    if frequency == "weekly":
        # Move to next matching weekday
        target_weekday_idx = _WEEKDAYS.index(weekday.lower()) if weekday.lower() in _WEEKDAYS else 0
        days_ahead = target_weekday_idx - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        if days_ahead == 0 and target > now:
            pass  # this week's target is still ahead today
        else:
            # Go to next occurrence of this weekday
            from datetime import timedelta
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            target += timedelta(days=days_ahead)
            if target <= now:
                target += timedelta(days=7)

    return target


def _scheduler_thread_fn() -> None:
    """Background thread that waits for schedule time then triggers backup."""
    app_log("[sched_backup.scheduler] Started.")
    while not _scheduler_stop.is_set():
        sched_cfg = get_scheduled_config()
        if not sched_cfg.get("enabled", False):
            _scheduler_stop.wait(60)  # check every minute
            continue

        next_time = get_next_backup_time()
        now = datetime.now()
        if next_time > now:
            wait_secs = (next_time - now).total_seconds()
            app_log(f"[sched_backup.scheduler] Next backup in {wait_secs:.0f}s ({next_time.strftime('%Y-%m-%d %H:%M')})")
            # Sleep in small chunks so we can respond to stop signal
            while wait_secs > 0 and not _scheduler_stop.wait(min(wait_secs, 30)):
                wait_secs -= 30
        else:
            # We reached the scheduled time — run backup
            try:
                # Small window check: ensure we haven't already backed up
                # within the last hour (prevent double-run on restart)
                last = sched_cfg.get("last_backup", "")
                if last:
                    try:
                        last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M")
                        if (datetime.now() - last_dt).total_seconds() < 3600:
                            app_log("[sched_backup.scheduler] Recent backup detected, skipping.")
                        else:
                            run_scheduled_backup()
                    except ValueError:
                        run_scheduled_backup()
                else:
                    run_scheduled_backup()
            except Exception as e:
                app_log(f"[sched_backup.scheduler] Backup failed: {e}")
                sched_cfg["last_error"] = str(e)[:200]
                save_scheduled_config(sched_cfg)

    app_log("[sched_backup.scheduler] Stopped.")


def start_scheduler() -> None:
    """Start the background scheduler thread (idempotent)."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_thread_fn,
        name="ScheduledBackup",
        daemon=True,
    )
    _scheduler_thread.start()
    app_log("[sched_backup.scheduler] Thread started.")


def stop_scheduler() -> None:
    """Signal the scheduler to stop and wait briefly."""
    _scheduler_stop.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=5)
