"""Workflow layer for staff data."""

from __future__ import annotations

from collections import defaultdict

from repositories.attendance_repo import AttendanceRepository
from repositories.staff_repo import StaffRepository


class StaffService:
    def __init__(self, repo: StaffRepository | None = None, attendance_repo: AttendanceRepository | None = None):
        self.repo = repo or StaffRepository()
        self.attendance_repo = attendance_repo or AttendanceRepository()

    def list_staff(self) -> list[dict]:
        return self.repo.list_all()

    def save_legacy_staff(self, payload: dict) -> None:
        self.repo.upsert_legacy_staff(payload)

    def build_legacy_staff_map(self) -> dict:
        sessions_by_staff = defaultdict(list)
        for row in self.attendance_repo.list_all():
            sessions_by_staff[row.get("staff_name", "")].append(row)
        result = {}
        for staff in self.repo.list_all():
            name = staff.get("legacy_name", "")
            by_day: dict[str, dict] = {}
            for session in sessions_by_staff.get(name, []):
                day = session.get("attendance_date", "")
                entry = by_day.setdefault(day, {
                    "date": day,
                    "status": session.get("status", "Present"),
                    "sessions": [],
                })
                entry["status"] = session.get("status", entry.get("status", "Present"))
                entry["sessions"].append({
                    "in_time": session.get("in_time", ""),
                    "out_time": session.get("out_time", ""),
                })
                if session.get("in_time") and not entry.get("in_time"):
                    entry["in_time"] = session.get("in_time", "")
                if session.get("out_time"):
                    entry["out_time"] = session.get("out_time", "")
            result[name] = {
                "name": staff.get("display_name", name),
                "role": staff.get("role_name", "staff"),
                "phone": staff.get("phone", ""),
                "commission_pct": float(staff.get("commission_pct", 0.0) or 0.0),
                "salary": float(staff.get("salary", 0.0) or 0.0),
                "photo": staff.get("photo_path", ""),
                "inactive": not bool(staff.get("active", 1)),
                "attendance": list(by_day.values()),
                "sales": [],
            }
        return result

    def sync_legacy_staff_map(self, data: dict) -> None:
        for key, staff in data.items():
            self.repo.upsert_legacy_staff({
                "legacy_name": key,
                "display_name": staff.get("name", key),
                "role_name": staff.get("role", "staff"),
                "phone": staff.get("phone", ""),
                "commission_pct": float(staff.get("commission_pct", 0.0) or 0.0),
                "salary": float(staff.get("salary", 0.0) or 0.0),
                "active": not bool(staff.get("inactive", False)),
                "photo_path": staff.get("photo", ""),
                "notes": "",
            })
            sessions = []
            for day in staff.get("attendance", []) or []:
                day_sessions = day.get("sessions", []) or []
                if day_sessions:
                    for session in day_sessions:
                        sessions.append({
                            "attendance_date": day.get("date", ""),
                            "status": day.get("status", "Present"),
                            "in_time": session.get("in_time", ""),
                            "out_time": session.get("out_time", ""),
                            "source": "staff_ui",
                        })
                else:
                    sessions.append({
                        "attendance_date": day.get("date", ""),
                        "status": day.get("status", "Present"),
                        "in_time": day.get("in_time", ""),
                        "out_time": day.get("out_time", ""),
                        "source": "staff_ui",
                    })
            self.attendance_repo.replace_staff_sessions(key, sessions)