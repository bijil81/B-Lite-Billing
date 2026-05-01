from __future__ import annotations

from src.blite_v6.settings.backup_license_about import (
    LICENSE_ACTIVATION_NOTE,
    UPDATE_MANIFEST_HELP_TEXT,
    VC_RUNTIME_HELP_TEXT,
    about_context_data,
    about_contact_rows,
    about_version_rows,
    activity_count_text,
    backup_context_data,
    backup_info_text,
    build_backup_schedule_config,
    build_update_manifest_payload,
    license_context_data,
    license_reminder_text,
    license_status_rows,
    update_available_message,
    vc_runtime_status,
)


def test_backup_schedule_and_info_text_preserve_existing_fallbacks():
    cfg = build_backup_schedule_config(
        enabled=True,
        frequency="weekly",
        time="02:30",
        retention="bad",
        weekday="friday",
    )

    assert cfg == {
        "enabled": True,
        "frequency": "weekly",
        "time": "02:30",
        "retention": 7,
        "weekday": "friday",
    }
    assert build_backup_schedule_config(
        enabled=False,
        frequency="daily",
        time="01:00",
        retention="12",
        weekday="monday",
    )["retention"] == 12
    assert backup_info_text({"last_backup": "Today"}) == "Last backup: Today"
    assert backup_info_text({"last_backup": "Yesterday", "last_error": "Disk full"}) == (
        "Last backup: Yesterday\nLast error: Disk full"
    )
    assert activity_count_text("bad") == "Total entries: 0"
    assert activity_count_text(9) == "Total entries: 9"


def test_license_rows_reminder_and_context_data():
    status = {
        "device_id": "abcdefghijklmnopqrstuvwxyz",
        "install_id": "install-1",
        "activated": False,
        "days_left": 2,
        "expired": False,
        "date_tamper_detected": True,
        "code_tamper_detected": False,
        "activation_disabled": True,
        "reminder_required": True,
    }

    rows = license_status_rows(status)
    assert rows[0] == ("Device ID", "abcdefghijklmnopqrstuvwx...")
    assert ("Install ID", "install-1") in rows
    assert ("Activated", "No") in rows
    assert ("Trial Status", "Active") in rows
    assert ("Date Tamper", "Detected") in rows
    assert ("Activation Disabled", "Yes") in rows
    assert license_reminder_text(status) == "Reminder: trial ends in 2 day(s). Activate before expiry."
    assert "Activation is fully offline" in LICENSE_ACTIVATION_NOTE

    context = license_context_data(status, "Install ID")
    assert context["entity_type"] == "license_status"
    assert context["selected_text"] == "install-1"
    assert context["selected_row"]["selected_key"] == "install_id"
    assert context["extra"] == {"has_device_id": True, "has_install_id": True}


def test_license_rows_show_lifetime_after_activation():
    status = {
        "device_id": "abcdefghijklmnopqrstuvwxyz",
        "install_id": "install-1",
        "activated": True,
        "days_left": 15,
        "expired": False,
        "date_tamper_detected": False,
        "code_tamper_detected": False,
        "activation_disabled": False,
        "reminder_required": False,
    }

    rows = license_status_rows(status)

    assert ("Activated", "Yes") in rows
    assert ("Days Left", "Lifetime") in rows
    assert ("Trial Status", "Activated") in rows
    assert license_reminder_text(status) == ""


def test_about_version_vc_update_and_manifest_helpers():
    assert about_version_rows(
        app_name="B-Lite",
        version="5.6",
        company="B-Lite Technologies",
        is_frozen=False,
    ) == [
        ("Application", "B-Lite"),
        ("Version", "v5.6"),
        ("Publisher", "B-Lite Technologies"),
        ("Mode", "Development (Source)"),
    ]
    assert about_version_rows(app_name="B-Lite", version="6.0", company="B-Lite", is_frozen=True)[3] == (
        "Mode",
        "Installed (EXE)",
    )
    assert about_contact_rows({}) == []
    assert about_contact_rows(
        {
            "name": "B-Lite Support",
            "phone": "9999999999",
            "email": "",
            "note": "For license help",
        }
    ) == [
        ("Name", "B-Lite Support"),
        ("Phone", "9999999999"),
        ("Note", "For license help"),
    ]
    assert vc_runtime_status(True) == ("VC++ Runtime: Detected", "#27ae60")
    assert vc_runtime_status(False) == ("VC++ Runtime: Not detected", "#e67e22")
    assert "VC++ 2015-2022" in VC_RUNTIME_HELP_TEXT
    assert "file:///" in UPDATE_MANIFEST_HELP_TEXT

    msg, has_download = update_available_message(
        {"version": "6.0", "changelog": "Fixes", "download_url": "https://example.com"}
    )
    assert msg == "Version 6.0 is available!\n\nFixes\n\nOpen download page?"
    assert has_download is True
    assert update_available_message({"version": "6.0"}) == ("Version 6.0 is available!", False)

    payload = build_update_manifest_payload({"salon_name": "Demo"}, "  file:///C:/update.json ")
    assert payload == {"salon_name": "Demo", "update_manifest_url": "file:///C:/update.json"}


def test_context_data_builders():
    assert backup_context_data(" C:/Backups ") == {
        "entity_type": "backup_folder",
        "selected_row": {"folder_path": "C:/Backups"},
        "selected_text": "C:/Backups",
        "widget_id": "settings_backup_folder",
        "extra": {"has_backup_folder": True},
    }
    assert backup_context_data("")["extra"] == {"has_backup_folder": False}

    about = about_context_data(" https://example.com/update.json ")
    assert about["entity_type"] == "update_manifest"
    assert about["selected_text"] == "https://example.com/update.json"
    assert about["extra"] == {"has_manifest_url": True}


def test_salon_settings_imports_phase7_helpers():
    import salon_settings
    from src.blite_v6.settings import backup_license_about

    assert salon_settings.license_status_rows is backup_license_about.license_status_rows
    assert salon_settings.about_version_rows is backup_license_about.about_version_rows
    assert salon_settings.about_contact_rows is backup_license_about.about_contact_rows
    assert salon_settings.backup_context_data is backup_license_about.backup_context_data
    assert salon_settings.build_update_manifest_payload is backup_license_about.build_update_manifest_payload
