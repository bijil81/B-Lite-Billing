from __future__ import annotations

from typing import Mapping

from branding import get_company_name


def parse_print_width(width_text: str, default: int = 48) -> int:
    try:
        return int(str(width_text).strip())
    except Exception:
        return default


def build_print_settings_payload(
    current_settings: Mapping,
    *,
    paper_size: str,
    font_size: int,
    width_text: str,
) -> dict:
    cfg = dict(current_settings)
    cfg["paper_size"] = paper_size
    cfg["print_font_size"] = int(font_size)
    cfg["print_width_chars"] = parse_print_width(width_text)
    return cfg


def print_settings_saved_message(settings: Mapping) -> str:
    paper = settings.get("paper_size", "80mm")
    width = str(settings.get("print_width_chars", 48))
    font_size = str(settings.get("print_font_size", 9))
    return f"Print settings saved!\nPaper: {paper}  Width: {width}  Font: {font_size}pt"


def build_print_preview_text(
    settings: Mapping,
    *,
    paper_size: str,
    font_size: int,
    width_text: str,
) -> str:
    width = parse_print_width(width_text)
    shop_name = str(settings.get("salon_name", get_company_name()))[:width]
    address = str(settings.get("address", "Kollam, Kerala"))[:width]
    return (
        f"{shop_name:^{width}}\n"
        f"{address:^{width}}\n"
        + "=" * width + "\n"
        + "Invoice : INV00001     18-03-2026\n"
        + "Customer: Sample Customer\n"
        + "=" * width + "\n"
        + f"{'Hair Cut':<{width - 22}} {'1':>3} {'300':>7} {'300.00':>9}\n"
        + f"{'Facial':<{width - 22}} {'1':>3} {'600':>7} {'600.00':>9}\n"
        + "-" * width + "\n"
        + f"{'GRAND TOTAL':>{width - 10}} {'900.00':>10}\n"
        + "=" * width + "\n"
        + f"Paper:{paper_size}  Width:{width} cols  Font:{font_size}pt"
    )

