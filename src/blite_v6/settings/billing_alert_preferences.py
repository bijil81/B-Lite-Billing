from __future__ import annotations

ALERT_PREF_KEY = "show_below_cost_alert"


def is_below_cost_alert_enabled(settings) -> bool:
    try:
        if settings is None:
            return True
        return bool(settings.get(ALERT_PREF_KEY, True))
    except Exception:
        return True
