from __future__ import annotations

from typing import Any


TotalsTuple = tuple[float, float, float, float, float, float, float, float, float, float]


def has_bill_items(bill_items: list[dict[str, Any]] | None) -> bool:
    return bool(bill_items)


def save_report_args_from_totals(totals: TotalsTuple) -> dict[str, float]:
    return {
        "final": totals[8],
        "disc": totals[3],
        "pts_disc": totals[5],
        "offer_disc": totals[6],
        "redeem_disc": totals[7],
        "mem_disc": totals[4],
    }


def bill_action_empty_warning() -> tuple[str, str]:
    return "Warning", "Bill is empty!"


def bill_saved_message(path: str) -> tuple[str, str]:
    return "Saved", f"Bill saved:\n{path}"


def pdf_saved_message(path: str) -> tuple[str, str]:
    return "Saved", f"PDF saved:\n{path}"


def save_error_message(error: Exception | str) -> tuple[str, str]:
    return "Error", f"Could not save:\n{error}"


def pdf_error_message(error: Exception | str) -> tuple[str, str]:
    return "Error", f"Could not save PDF:\n{error}"


def print_error_message(error: Exception | str) -> tuple[str, str]:
    return (
        "Print Error",
        f"Could not print:\n{error}\n\nMake sure thermal printer is set as default.",
    )


def printed_message(printer_name: str) -> tuple[str, str]:
    return "Printed", f"Printed to: {printer_name}"


def should_auto_clear_after_print(settings: dict[str, Any]) -> bool:
    return bool(settings.get("auto_clear_after_print", False))
