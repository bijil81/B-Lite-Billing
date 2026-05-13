# Print Build Note

## Current production logic
- `PRINT` button saves the bill and then tries direct Windows printer output.
- If direct printer output is unavailable or errors out, the app falls back to generated PDF.
- `PDF` button generates PDF and saves the bill.
- Printerless systems are expected to work via PDF output.

## Required build dependencies for direct Windows printing
- Python package: `pywin32`
- Project file already includes it: [requirements.txt](../requirements.txt)
- PyInstaller spec already includes hidden imports:
  - `win32api`
  - `win32print`
  - file: [WhiteLabelApp.spec](../WhiteLabelApp.spec)

## Pre-build checklist
1. Run `pip install -r requirements.txt`
2. Verify direct print modules import:
   - `python -c "import win32print, win32api"`
3. Build the EXE only after that check passes.

## Windows service / printer notes
- `Print Spooler` must be **Running** for Windows printer enumeration and virtual printers.
- `Startup type = Automatic` alone is not enough; the service must actually be running.
- If Spooler is blocked by Windows permissions or policy, direct printer printing may fail even if `pywin32` is installed.

## Microsoft Print to PDF
- It is useful for Windows printer stack validation.
- It is **not** the primary recommended thermal test path for this app, because direct print uses RAW/text printer output.
- For printerless smoke, prefer:
  1. Billing `PRINT` -> PDF fallback
  2. Billing `PDF` button
  3. template render smoke PDFs

## Hardware-free smoke we completed
Generated and visually checked PDF renders for:
- `thermal_58mm`
- `thermal_72mm`
- `thermal_76mm`
- `thermal_80mm`
- `thermal_112mm`
- `a5_halfpage`
- `a4_standard`
- `invoice_compact`
- `invoice_detailed`

Output folder:
- [print_smoke_outputs](manual_test_samples/print_smoke_outputs)

## Visual QA result
- No text clipping found on thermal widths in current smoke sample.
- No line-wrap break found on tested sample item names.
- No footer truncation found.
- A4/A5 templates have large bottom whitespace, but that is not a blocking defect.

## Installed EXE smoke result
- Status: PASS.
- The latest EXE was built and installed by the user.
- Installed application opened successfully.
- All main tabs opened without reported issue.
- No installer/startup/tab-load blocker was observed in the manual smoke.

## Real final printer smoke before release
Use at least:
1. one 58mm or 72/80mm thermal printer
2. one A4 office printer or PDF-equivalent print path
3. one sample with long item names
4. one sample with discount / GST / membership / wallet / due lines

## Recommended release stance
- If shop has no printer configured yet, shipping is still acceptable because PDF fallback works.
- For shops using thermal printing, perform one final on-device print smoke after EXE rebuild.
