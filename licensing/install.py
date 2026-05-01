from datetime import datetime, timezone
import uuid
from .storage import load_record, save_record

INSTALL_FILE = "install.dat"
TRIAL_DAYS = 15
EXTENSION_DAYS = 10


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_install_state():
    state = load_record(INSTALL_FILE)
    if state:
        changed = False
        defaults = {
            "trial_days_total": TRIAL_DAYS,
            "trial_extension_days": EXTENSION_DAYS,
            "trial_extension_used": False,
            "trial_extended_utc": "",
            "last_opened_utc": state.get("first_install_utc", utc_now()),
            "activation_state": "trial",
            "activation_applied_utc": "",
            "date_tamper_detected": False,
            "code_tamper_detected": False,
        }
        for key, value in defaults.items():
            if key not in state:
                state[key] = value
                changed = True
        if changed:
            save_record(INSTALL_FILE, state)
        return state

    state = {
        "install_id": str(uuid.uuid4()).upper(),
        "first_install_utc": utc_now(),
        "last_opened_utc": utc_now(),
        "trial_days_total": TRIAL_DAYS,
        "trial_extension_days": EXTENSION_DAYS,
        "trial_extension_used": False,
        "trial_extended_utc": "",
        "activation_state": "trial",
        "activation_applied_utc": "",
        "date_tamper_detected": False,
        "code_tamper_detected": False,
    }
    save_record(INSTALL_FILE, state)
    return state


def mark_startup_and_detect_rollback(state):
    now = datetime.now(timezone.utc)
    try:
        last = datetime.fromisoformat(state.get("last_opened_utc", state["first_install_utc"]))
    except Exception:
        last = now
    if now < last:
        state["date_tamper_detected"] = True
    state["last_opened_utc"] = now.replace(microsecond=0).isoformat()
    save_record(INSTALL_FILE, state)
    return state["date_tamper_detected"]
