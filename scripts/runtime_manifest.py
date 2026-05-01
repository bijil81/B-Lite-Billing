from __future__ import annotations

REQUIRED_PYTHON_PREFIX = "3.12."

# Files under dist/<app>/_internal that must exist for the packaged app
# to boot and support the currently shipped offline feature set.
REQUIRED_RUNTIME_FILES = [
    "python3.dll",
    "python312.dll",
    "_tkinter.pyd",
    "sqlite3.dll",
    "tcl86t.dll",
    "tk86t.dll",
    "bcrypt/_bcrypt.pyd",
    "pywin32_system32/pywintypes312.dll",
    "selenium/webdriver/common/windows/selenium-manager.exe",
    "sql/v5_schema.sql",
]

# Optional convenience/runtime extras that may exist in some builds.
# Missing entries here should not fail the release build.
OPTIONAL_RUNTIME_FEATURES = {
    "internal_pdf_preview": [
        "pymupdf/_mupdf.pyd",
        "pymupdf/mupdfcpp64.dll",
    ],
}
