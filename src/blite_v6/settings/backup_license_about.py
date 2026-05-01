from __future__ import annotations

from typing import Mapping


LICENSE_ACTIVATION_NOTE = (
    "Activation is fully offline. Keys are tied to this device and install.\n"
    "Trial reminder starts on day 12. After expiry, the app will block at startup.\n"
    "Tampered license or modified critical files disable activation."
)

VC_RUNTIME_HELP_TEXT = (
    "The VC++ 2015-2022 redistributable is needed for packaged builds.\n"
    "If missing, install it from Microsoft's website."
)

UPDATE_MANIFEST_HELP_TEXT = "Use a local file URL like file:///C:/path/update.json or an HTTPS manifest URL."


def build_backup_schedule_config(
    *,
    enabled: bool,
    frequency: str,
    time: str,
    retention: str,
    weekday: str,
) -> dict:
    return {
        "enabled": bool(enabled),
        "frequency": str(frequency),
        "time": str(time),
        "retention": int(retention) if str(retention).isdigit() else 7,
        "weekday": str(weekday),
    }


def backup_info_text(schedule_config: Mapping) -> str:
    text = f"Last backup: {schedule_config.get('last_backup', 'Never')}"
    last_error = str(schedule_config.get("last_error", ""))
    if last_error:
        text += f"\nLast error: {last_error}"
    return text


def activity_count_text(count: object) -> str:
    try:
        total = int(count)
    except Exception:
        total = 0
    return f"Total entries: {total}"


def license_status_rows(status: Mapping) -> list[tuple[str, str]]:
    device_id = str(status.get("device_id", ""))
    activated = bool(status.get("activated"))
    days_left = "Lifetime" if activated else str(status.get("days_left", ""))
    trial_status = "Activated" if activated else ("Expired" if status.get("expired") else "Active")
    return [
        ("Device ID", device_id[:24] + "..."),
        ("Install ID", str(status.get("install_id", ""))),
        ("Activated", "Yes" if activated else "No"),
        ("Days Left", days_left),
        ("Trial Status", trial_status),
        ("Date Tamper", "Detected" if status.get("date_tamper_detected") else "No"),
        ("Code Tamper", "Detected" if status.get("code_tamper_detected") else "No"),
        ("Activation Disabled", "Yes" if status.get("activation_disabled") else "No"),
    ]


def license_reminder_text(status: Mapping) -> str:
    if status.get("reminder_required") and not status.get("activated"):
        return f"Reminder: trial ends in {status.get('days_left')} day(s). Activate before expiry."
    return ""


def about_version_rows(*, app_name: str, version: str, company: str, is_frozen: bool) -> list[tuple[str, str]]:
    return [
        ("Application", str(app_name)),
        ("Version", f"v{version}"),
        ("Publisher", str(company)),
        ("Mode", "Installed (EXE)" if is_frozen else "Development (Source)"),
    ]


def about_contact_rows(contact_info: Mapping) -> list[tuple[str, str]]:
    labels = (
        ("name", "Name"),
        ("phone", "Phone"),
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("website", "Website"),
        ("address", "Address"),
        ("note", "Note"),
    )
    rows = []
    for key, label in labels:
        value = str(contact_info.get(key, "") or "").strip()
        if value:
            rows.append((label, value))
    return rows


def vc_runtime_status(detected: bool) -> tuple[str, str]:
    if detected:
        return "VC++ Runtime: Detected", "#27ae60"
    return "VC++ Runtime: Not detected", "#e67e22"


def update_available_message(info: Mapping) -> tuple[str, bool]:
    version = info.get("version", "?")
    notes = info.get("changelog", "")
    download_url = info.get("download_url", "")
    message = f"Version {version} is available!"
    if notes:
        message += f"\n\n{notes}"
    if download_url:
        message += "\n\nOpen download page?"
    return message, bool(download_url)


def build_update_manifest_payload(current_settings: Mapping, manifest_url: str) -> dict:
    cfg = dict(current_settings)
    cfg["update_manifest_url"] = str(manifest_url).strip()
    return cfg


def backup_context_data(folder_path: str) -> dict:
    folder = str(folder_path).strip()
    return {
        "entity_type": "backup_folder",
        "selected_row": {"folder_path": folder},
        "selected_text": folder,
        "widget_id": "settings_backup_folder",
        "extra": {"has_backup_folder": bool(folder)},
    }


def license_context_data(status: Mapping, field_label: str = "") -> dict:
    device_id = str(status.get("device_id", "")).strip()
    install_id = str(status.get("install_id", "")).strip()
    selected_key = "install_id" if field_label == "Install ID" else "device_id"
    selected_value = install_id if selected_key == "install_id" else device_id
    return {
        "entity_type": "license_status",
        "selected_row": {
            "device_id": device_id,
            "install_id": install_id,
            "selected_key": selected_key,
            "selected_value": selected_value,
        },
        "selected_text": selected_value,
        "widget_id": "settings_license_status",
        "extra": {
            "has_device_id": bool(device_id),
            "has_install_id": bool(install_id),
        },
    }


def about_context_data(manifest_url: str) -> dict:
    url = str(manifest_url).strip()
    return {
        "entity_type": "update_manifest",
        "selected_row": {"manifest_url": url},
        "selected_text": url,
        "widget_id": "settings_manifest_url",
        "extra": {"has_manifest_url": bool(url)},
    }
