"""Appointment validators for v5 services."""

from __future__ import annotations

from validators.common_validators import require_text


def validate_appointment_payload(payload: dict) -> dict:
    return {
        **payload,
        "appointment_date": require_text(payload.get("appointment_date"), "appointment_date"),
        "appointment_time": require_text(payload.get("appointment_time"), "appointment_time"),
        "customer_name": require_text(payload.get("customer_name"), "customer_name"),
        "phone": str(payload.get("phone", "") or "").strip(),
        "service_name": str(payload.get("service_name", "") or "").strip(),
        "staff_name": str(payload.get("staff_name", "") or "").strip(),
        "status": str(payload.get("status", "Scheduled") or "Scheduled").strip(),
    }
