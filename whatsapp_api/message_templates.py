"""Optional WhatsApp API message templates."""

from __future__ import annotations


DEFAULT_TEMPLATES = {
    "bill_ready": "Hello {customer_name}, your bill is ready from {salon_name}.",
    "appointment_reminder": "Reminder: your appointment at {salon_name} is at {time_slot}.",
}
