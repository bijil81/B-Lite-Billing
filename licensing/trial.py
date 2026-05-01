from datetime import datetime, timezone


def _parse_trial_datetime(raw_value):
    text = (raw_value or "").strip()
    if not text:
        raise ValueError("empty datetime")
    for fmt in (None, "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            parsed = datetime.fromisoformat(text) if fmt is None else datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            continue
    raise ValueError(f"Unsupported datetime format: {raw_value}")


def trial_status(state):
    """Compute trial status. Handles corrupted state gracefully."""
    first_install = state.get("first_install_utc", "")
    if not first_install:
        # No valid timestamp — treat as fresh install
        first_install = "2026-01-01T00:00:00+00:00"
    try:
        first = _parse_trial_datetime(first_install)
    except Exception:
        # Corrupt timestamp — default to now so user isn't locked out
        first = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    elapsed_days = max(0, (now - first).days)
    total_days = int(state.get('trial_days_total', 15))
    if state.get('trial_extension_used'):
        total_days += int(state.get('trial_extension_days', 10))
    days_left = max(0, total_days - elapsed_days)
    return {
        'elapsed_days': elapsed_days,
        'total_days': total_days,
        'days_left': days_left,
        'expired': elapsed_days >= total_days,
        'reminder_required': elapsed_days >= 12 and elapsed_days < total_days,
        'extension_available': not bool(state.get('trial_extension_used')),
    }
