"""Workflow layer for appointments."""

from __future__ import annotations

from repositories.appointments_repo import AppointmentsRepository
from validators.appointment_validator import validate_appointment_payload


class AppointmentService:
    def __init__(self, repo: AppointmentsRepository | None = None):
        self.repo = repo or AppointmentsRepository()

    def list_appointments(self, from_date: str = "", to_date: str = "") -> list[dict]:
        if from_date and to_date:
            return self.repo.list_by_date_range(from_date, to_date)
        return self.repo.list_all()

    def build_legacy_appointments(self) -> list[dict]:
        result = []
        for row in self.repo.list_all():
            result.append({
                "customer": row.get("customer_name", ""),
                "phone": row.get("phone", ""),
                "service": row.get("service_name", ""),
                "staff": row.get("staff_name", ""),
                "date": row.get("appointment_date", ""),
                "time": row.get("appointment_time", ""),
                "status": row.get("status", "Scheduled"),
                "dont_show": bool(row.get("dont_show", 0)),
                "last_reminded": row.get("last_reminded", ""),
                "notes": row.get("notes", ""),
            })
        return result

    def sync_legacy_appointments(self, data: list[dict]) -> None:
        for appt in data:
            self.save_legacy_appointment({
                "legacy_key": "|".join([
                    str(appt.get("phone", "") or ""),
                    str(appt.get("date", "") or ""),
                    str(appt.get("time", "") or ""),
                    str(appt.get("customer", "") or ""),
                ]),
                "customer_name": appt.get("customer", ""),
                "phone": appt.get("phone", ""),
                "service_name": appt.get("service", ""),
                "staff_name": appt.get("staff", ""),
                "appointment_date": appt.get("date", ""),
                "appointment_time": appt.get("time", ""),
                "status": appt.get("status", "Scheduled"),
                "dont_show": appt.get("dont_show", False),
                "last_reminded": appt.get("last_reminded", ""),
                "notes": appt.get("notes", ""),
            })

    def save_legacy_appointment(self, payload: dict) -> None:
        clean = validate_appointment_payload(payload)
        self.repo.upsert_legacy_appointment({
            **clean,
            "legacy_key": payload.get("legacy_key") or f"{clean['phone']}|{clean['appointment_date']}|{clean['appointment_time']}|{clean['customer_name']}",
        })