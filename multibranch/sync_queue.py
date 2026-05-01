"""Queue helpers for optional branch-safe sync."""

from __future__ import annotations


def queue_entry(entity_type: str, entity_id: str, action: str, payload: dict | None = None) -> dict:
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "payload": payload or {},
    }
