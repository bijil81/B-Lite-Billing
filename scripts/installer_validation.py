from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "WhiteLabelInstaller.nsi"

REQUIRED_SNIPPETS = [
    '!define INSTALL_DIR     "$PROGRAMFILES\\${WL_INSTALL_DIR_NAME}"',
    'InstallDir        "${INSTALL_DIR}"',
    'File /r "dist\\${WL_DIST_DIR}\\*"',
    '!define REG_KEY         "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${WL_RUNTIME_DIR_NAME}"',
]

FORBIDDEN_SNIPPETS = [
    'File /r "dist\\${WL_DIST_DIR}\\*.*"',
]


def main() -> int:
    text = INSTALLER.read_text(encoding="utf-8", errors="replace")
    missing = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in text]
    forbidden = [snippet for snippet in FORBIDDEN_SNIPPETS if snippet in text]
    ok = not missing and not forbidden
    print(json.dumps({
        "installer_script": str(INSTALLER),
        "missing_required_snippets": missing,
        "forbidden_snippets_present": forbidden,
        "ok": ok,
    }, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
