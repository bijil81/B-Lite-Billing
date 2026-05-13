from src.blite_v6.billing.printer_detection import (
    PrinterInfo,
    is_virtual_printer,
    resolve_print_route,
)


class FakeWin32Print:
    PRINTER_ENUM_LOCAL = 2
    PRINTER_ENUM_CONNECTIONS = 4

    def __init__(self, default_name, printers):
        self.default_name = default_name
        self.printers = printers

    def GetDefaultPrinter(self):
        return self.default_name

    def EnumPrinters(self, flags, name, level):
        if level != 2:
            return []
        return self.printers


def printer_tuple(name, port="USB001", driver="Thermal Receipt Driver"):
    # Pywin32 level-2 tuple layout uses index 1/3/4 for name/port/driver.
    return (None, name, "", port, driver)


def test_detects_virtual_printer_from_name():
    assert is_virtual_printer(PrinterInfo("Microsoft Print to PDF"))
    assert is_virtual_printer(PrinterInfo("Send To OneNote 2016"))
    assert is_virtual_printer(PrinterInfo("Microsoft XPS Document Writer"))


def test_detects_virtual_printer_from_driver_or_port_metadata():
    assert is_virtual_printer(
        PrinterInfo("Office Printer", driver_name="Microsoft Print To PDF Driver")
    )
    assert is_virtual_printer(
        PrinterInfo("Document Writer", port_name="PORTPROMPT: XPS")
    )


def test_routes_virtual_default_to_pdf_fallback():
    win32print = FakeWin32Print(
        "Microsoft Print to PDF",
        [
            printer_tuple("Microsoft Print to PDF", "PORTPROMPT:", "Microsoft Print To PDF"),
            printer_tuple("Receipt Printer"),
        ],
    )

    route = resolve_print_route(win32print)

    assert route.use_pdf_fallback is True
    assert route.printer_name == "Microsoft Print to PDF"
    assert "Virtual printer selected" in route.detail


def test_routes_physical_printer_to_direct_print_path():
    win32print = FakeWin32Print(
        "Receipt Printer",
        [
            printer_tuple("Microsoft XPS Document Writer", "PORTPROMPT:", "XPS"),
            printer_tuple("Receipt Printer", "USB001", "Thermal Receipt Driver"),
        ],
    )

    route = resolve_print_route(win32print)

    assert route.use_pdf_fallback is False
    assert route.printer_name == "Receipt Printer"
