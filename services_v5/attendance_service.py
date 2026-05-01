"""Workflow layer for attendance sessions."""

from __future__ import annotations

from repositories.attendance_repo import AttendanceRepository


class AttendanceService:
    def __init__(self, repo: AttendanceRepository | None = None):
        self.repo = repo or AttendanceRepository()

    def list_daily_sessions(self, attendance_date: str) -> list[dict]:
        return self.repo.list_by_date(attendance_date)

    def add_session(self, payload: dict) -> None:
        self.repo.add_session(payload)
