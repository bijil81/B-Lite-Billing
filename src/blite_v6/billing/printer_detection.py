from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VIRTUAL_PRINTER_TOKENS = (
    "microsoft print to pdf",
    "microsoft xps document writer",
    "onenote",
    "send to onenote",
    "pdf",
    "xps",
)


@dataclass(frozen=True)
class PrinterInfo:
    name: str
    driver_name: str = ""
    port_name: str = ""


@dataclass(frozen=True)
class PrintRoute:
    use_pdf_fallback: bool
    printer_name: str = ""
    detail: str = ""


def _field(value: Any, key: str, index: int) -> str:
    if isinstance(value, dict):
        return str(value.get(key) or "")
    try:
        return str(value[index] or "")
    except Exception:
        return ""


def _first_field(value: Any, key: str, indexes: tuple[int, ...]) -> str:
    for index in indexes:
        field = _field(value, key, index)
        if field:
            return field
    return ""


def is_virtual_printer(printer: PrinterInfo | str | None) -> bool:
    if isinstance(printer, PrinterInfo):
        haystack = " ".join(
            part for part in (printer.name, printer.driver_name, printer.port_name) if part
        ).lower()
    else:
        haystack = str(printer or "").lower()
    return any(token in haystack for token in VIRTUAL_PRINTER_TOKENS)


def list_printers(win32print: Any) -> list[PrinterInfo]:
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers: list[PrinterInfo] = []
    for level in (2, 1):
        try:
            raw_printers = win32print.EnumPrinters(flags, None, level)
        except Exception:
            continue
        for item in raw_printers:
            if level == 2:
                name = _first_field(item, "pPrinterName", (1, 2))
                driver_name = _field(item, "pDriverName", 4)
                port_name = _field(item, "pPortName", 3)
            else:
                name = _field(item, "pName", 2)
                driver_name = _field(item, "pDescription", 1)
                port_name = ""
            if name and all(existing.name.lower() != name.lower() for existing in printers):
                printers.append(PrinterInfo(name=name, driver_name=driver_name, port_name=port_name))
        if printers:
            break
    return printers


def resolve_print_route(win32print: Any, preferred_printer: str | None = None) -> PrintRoute:
    default_name = (preferred_printer or win32print.GetDefaultPrinter() or "").strip()
    printers = list_printers(win32print)
    selected = next(
        (printer for printer in printers if printer.name.lower() == default_name.lower()),
        PrinterInfo(default_name),
    )

    if not selected.name:
        physical = next((printer for printer in printers if not is_virtual_printer(printer)), None)
        if physical:
            return PrintRoute(False, physical.name, f"No default printer; using detected printer: {physical.name}")
        return PrintRoute(True, "", "No usable printer was detected.")

    if is_virtual_printer(selected):
        detail = f"Virtual printer selected: {selected.name}"
        if selected.driver_name:
            detail += f" ({selected.driver_name})"
        return PrintRoute(True, selected.name, detail)

    return PrintRoute(False, selected.name, f"Direct printer selected: {selected.name}")
