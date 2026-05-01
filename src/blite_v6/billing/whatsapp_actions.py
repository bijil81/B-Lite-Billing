from __future__ import annotations

from typing import Any, Mapping


def invalid_phone_message() -> tuple[str, str]:
    return "Invalid Phone", "Enter a valid 10-digit phone number."


def whatsapp_send_success_message() -> tuple[str, str]:
    return (
        "WhatsApp",
        "WhatsApp bill flow completed.\nMessage was sent or auto-sent successfully.",
    )


def whatsapp_manual_send_message(message: str = "") -> tuple[str, str]:
    detail = message or "WhatsApp opened in your browser."
    return (
        "WhatsApp",
        f"{detail}\n\nClick Send in WhatsApp to finish. Auto-send is available only when the app-controlled WhatsApp session is ready.",
    )


def whatsapp_send_error_message(error: str) -> tuple[str, str]:
    return (
        "WhatsApp Error",
        f"Could not send bill.\n\n{error}\n\nUse WA? to log in first if needed.",
    )


def whatsapp_exception_message(error: Exception | str) -> tuple[str, str]:
    return (
        "WhatsApp Error",
        f"Could not send:\n{error}\n\nMake sure WhatsApp Web is open and logged in.",
    )


def extract_whatsapp_error(snapshot: Mapping[str, Any]) -> str:
    return snapshot.get("last_error") or snapshot.get("message") or "Unknown WhatsApp error"


def whatsapp_status_view(status: str) -> dict[str, str]:
    views = {
        "opening": {"text": "WA: Opening", "color_key": "blue", "hover": "#154360"},
        "sending": {"text": "WA: Sending", "color_key": "orange", "hover": "gold"},
        "ready": {"text": "WA: Ready", "color_key": "green", "hover": "#1e8449"},
        "browser": {"text": "WA: Browser", "color_key": "green", "hover": "#1e8449"},
        "login": {"text": "WA: Login", "color_key": "red", "hover": "#922b21"},
        "scan_qr": {"text": "WA: Scan QR", "color_key": "orange", "hover": "gold"},
        "manual": {"text": "WA: Manual", "color_key": "orange", "hover": "gold"},
        "error": {"text": "WA: Error", "color_key": "red", "hover": "#922b21"},
    }
    return views[status]


def whatsapp_session_result(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    state = snapshot.get("state")
    if state == "READY":
        return {
            "status": "ready",
            "message": ("WhatsApp", "WhatsApp Web is connected and ready."),
            "message_kind": "info",
        }
    if state == "WAITING_FOR_LOGIN":
        detail = snapshot.get("message") or "WhatsApp Web opened."
        return {
            "status": "scan_qr",
            "message": (
                "WhatsApp",
                f"{detail}\nScan the QR code and keep the tab open.",
            ),
            "message_kind": "warning",
        }
    if state == "DEFAULT_BROWSER_OPEN":
        return {
            "status": "browser",
            "message": (
                "WhatsApp",
                "WhatsApp Web opened in your default browser.\n\n"
                "If WhatsApp is already logged in there, browser mode is ready.\n"
                "Auto-send still needs the app-controlled Edge/Chrome driver.",
            ),
            "message_kind": "info",
        }
    if state == "WAITING_MANUAL_SEND":
        return {
            "status": "manual",
            "message": whatsapp_manual_send_message(str(snapshot.get("message", ""))),
            "message_kind": "warning",
        }
    if state == "BROWSER_CLOSED":
        return {
            "status": "error",
            "message": (
                "WhatsApp Error",
                "WhatsApp browser is closed.\n\nClick WA again to reopen it.",
            ),
            "message_kind": "error",
        }
    if state in {"STARTING_BROWSER", "OPENING_WHATSAPP", "NOT_STARTED"}:
        return {"status": "opening", "message": None, "message_kind": None}
    return {
        "status": "error",
        "message": whatsapp_send_error_message(extract_whatsapp_error(snapshot)),
        "message_kind": "error",
    }
