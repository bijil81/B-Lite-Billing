"""Legacy appointments -> v5 appointments migration."""

from __future__ import annotations

from appointments import get_appointments
from repositories.appointments_repo import AppointmentsRepository


def migrate_appointments(dry_run: bool = True) -> dict:
    appointments = get_appointments()
    repo = AppointmentsRepository()
    migrated = []
    for appt in appointments:
        legacy_key = "|".join([
            str(appt.get("phone", "") or ""),
            str(appt.get("date", "") or ""),
            str(appt.get("time", "") or ""),
            str(appt.get("customer", "") or ""),
        ])
        payload = {
            "legacy_key": legacy_key,
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
        }
        if not dry_run:
            repo.upsert_legacy_appointment(payload)
        migrated.append(legacy_key)
    return {
        "source_count": len(appointments),
        "migrated": migrated,
        "dry_run": dry_run,
    }
