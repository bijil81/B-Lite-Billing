from __future__ import annotations


SESSION_CHECK_INTERVAL_MS = 60_000
MIN_SESSION_TIMEOUT_MINUTES = 5
DEFAULT_SESSION_TIMEOUT_MINUTES = 30


def session_timeout_minutes(settings: dict | None) -> int:
    try:
        raw = (settings or {}).get("session_timeout_minutes", DEFAULT_SESSION_TIMEOUT_MINUTES)
        return max(MIN_SESSION_TIMEOUT_MINUTES, int(raw or DEFAULT_SESSION_TIMEOUT_MINUTES))
    except Exception:
        return DEFAULT_SESSION_TIMEOUT_MINUTES


def should_auto_logout(settings: dict | None, last_activity_ts: float, now_ts: float) -> bool:
    settings = settings or {}
    if not bool(settings.get("auto_logout", False)):
        return False
    idle_limit_seconds = session_timeout_minutes(settings) * 60
    return (now_ts - last_activity_ts) >= idle_limit_seconds


def normalize_after_ids(after_info) -> list:
    if isinstance(after_info, str):
        return [after_info] if after_info else []
    try:
        return list(after_info)
    except Exception:
        return []
