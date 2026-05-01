from __future__ import annotations

from src.blite_v6.billing.whatsapp_actions import (
    extract_whatsapp_error,
    invalid_phone_message,
    whatsapp_manual_send_message,
    whatsapp_exception_message,
    whatsapp_send_error_message,
    whatsapp_send_success_message,
    whatsapp_session_result,
    whatsapp_status_view,
)


def test_whatsapp_messages_match_legacy_text():
    assert invalid_phone_message() == ("Invalid Phone", "Enter a valid 10-digit phone number.")
    assert whatsapp_send_success_message() == (
        "WhatsApp",
        "WhatsApp bill flow completed.\nMessage was sent or auto-sent successfully.",
    )
    assert whatsapp_manual_send_message("WhatsApp opened in default browser - manual Send required") == (
        "WhatsApp",
        "WhatsApp opened in default browser - manual Send required\n\nClick Send in WhatsApp to finish. Auto-send is available only when the app-controlled WhatsApp session is ready.",
    )
    assert whatsapp_send_error_message("login failed") == (
        "WhatsApp Error",
        "Could not send bill.\n\nlogin failed\n\nUse WA? to log in first if needed.",
    )
    assert whatsapp_exception_message("boom") == (
        "WhatsApp Error",
        "Could not send:\nboom\n\nMake sure WhatsApp Web is open and logged in.",
    )


def test_extract_whatsapp_error_priority_and_fallback():
    assert extract_whatsapp_error({"last_error": "last", "message": "message"}) == "last"
    assert extract_whatsapp_error({"message": "message"}) == "message"
    assert extract_whatsapp_error({}) == "Unknown WhatsApp error"


def test_whatsapp_status_views_match_button_texts():
    assert whatsapp_status_view("opening") == {"text": "WA: Opening", "color_key": "blue", "hover": "#154360"}
    assert whatsapp_status_view("sending")["text"] == "WA: Sending"
    assert whatsapp_status_view("ready")["text"] == "WA: Ready"
    assert whatsapp_status_view("browser")["text"] == "WA: Browser"
    assert whatsapp_status_view("login")["text"] == "WA: Login"
    assert whatsapp_status_view("scan_qr")["text"] == "WA: Scan QR"
    assert whatsapp_status_view("manual")["text"] == "WA: Manual"
    assert whatsapp_status_view("error")["text"] == "WA: Error"


def test_whatsapp_session_result_maps_ready_scan_and_error_states():
    assert whatsapp_session_result({"state": "READY"}) == {
        "status": "ready",
        "message": ("WhatsApp", "WhatsApp Web is connected and ready."),
        "message_kind": "info",
    }
    assert whatsapp_session_result({"state": "WAITING_FOR_LOGIN"}) == {
        "status": "scan_qr",
        "message": ("WhatsApp", "WhatsApp Web opened.\nScan the QR code and keep the tab open."),
        "message_kind": "warning",
    }
    assert whatsapp_session_result({"state": "DEFAULT_BROWSER_OPEN"}) == {
        "status": "browser",
        "message": (
            "WhatsApp",
            "WhatsApp Web opened in your default browser.\n\nIf WhatsApp is already logged in there, browser mode is ready.\nAuto-send still needs the app-controlled Edge/Chrome driver.",
        ),
        "message_kind": "info",
    }
    assert whatsapp_session_result({"state": "WAITING_MANUAL_SEND", "message": "WhatsApp opened in default browser"}) == {
        "status": "manual",
        "message": (
            "WhatsApp",
            "WhatsApp opened in default browser\n\nClick Send in WhatsApp to finish. Auto-send is available only when the app-controlled WhatsApp session is ready.",
        ),
        "message_kind": "warning",
    }
    assert whatsapp_session_result({"state": "BROWSER_CLOSED"}) == {
        "status": "error",
        "message": (
            "WhatsApp Error",
            "WhatsApp browser is closed.\n\nClick WA again to reopen it.",
        ),
        "message_kind": "error",
    }
    assert whatsapp_session_result({"state": "FAILED", "last_error": "driver missing"}) == {
        "status": "error",
        "message": ("WhatsApp Error", "Could not send bill.\n\ndriver missing\n\nUse WA? to log in first if needed."),
        "message_kind": "error",
    }
    assert whatsapp_session_result({"state": "OPENING_WHATSAPP"}) == {
        "status": "opening",
        "message": None,
        "message_kind": None,
    }
