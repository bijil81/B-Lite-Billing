"""Legacy staff -> v5 staff and attendance migration."""

from __future__ import annotations

from repositories.attendance_repo import AttendanceRepository
from repositories.staff_repo import StaffRepository
from staff import get_staff
from utils import attendance_get_sessions, attendance_sync_legacy_fields


def migrate_staff(dry_run: bool = True) -> dict:
    staff_data = get_staff()
    staff_repo = StaffRepository()
    attendance_repo = AttendanceRepository()
    migrated = []
    attendance_rows = 0
    for key, staff in staff_data.items():
        payload = {
            "legacy_name": key,
            "display_name": staff.get("name", key),
            "role_name": staff.get("role", "staff"),
            "phone": staff.get("phone", ""),
            "commission_pct": float(staff.get("commission_pct", 0.0) or 0.0),
            "salary": float(staff.get("salary", 0.0) or 0.0),
            "active": not bool(staff.get("inactive", False)),
            "photo_path": staff.get("photo", ""),
        }
        if not dry_run:
            staff_repo.upsert_legacy_staff(payload)
        migrated.append(key)
        for att in staff.get("attendance", []) or []:
            day = attendance_sync_legacy_fields(att)
            sessions = attendance_get_sessions(day)
            if sessions:
                for session in sessions:
                    attendance_rows += 1
                    if not dry_run:
                        attendance_repo.add_session({
                            "staff_name": key,
                            "attendance_date": day.get("date", ""),
                            "status": day.get("status", "Present"),
                            "in_time": session.get("in_time", ""),
                            "out_time": session.get("out_time", ""),
                            "source": "legacy_staff",
                        })
            else:
                attendance_rows += 1
                if not dry_run:
                    attendance_repo.add_session({
                        "staff_name": key,
                        "attendance_date": day.get("date", ""),
                        "status": day.get("status", "Present"),
                        "in_time": day.get("in_time", ""),
                        "out_time": day.get("out_time", ""),
                        "source": "legacy_staff",
                    })
    return {
        "source_count": len(staff_data),
        "migrated": migrated,
        "attendance_rows": attendance_rows,
        "dry_run": dry_run,
    }
