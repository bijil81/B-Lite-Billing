"""Compatibility adapter for staff and attendance v5 services."""

from __future__ import annotations

from salon_settings import get_settings
from services_v5.attendance_service import AttendanceService
from services_v5.staff_service import StaffService


_staff_service = StaffService()
_attendance_service = AttendanceService()


def use_v5_staff_db() -> bool:
    return bool(get_settings().get("use_v5_staff_db", False))


def list_staff_v5() -> list[dict]:
    return _staff_service.list_staff()


def list_attendance_sessions_v5(attendance_date: str) -> list[dict]:
    return _attendance_service.list_daily_sessions(attendance_date)


def get_staff_legacy_map_v5() -> dict:
    return _staff_service.build_legacy_staff_map()


def save_staff_legacy_map_v5(data: dict) -> None:
    _staff_service.sync_legacy_staff_map(data)