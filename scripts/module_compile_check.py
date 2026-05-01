from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]

MODULES = [
    ROOT / "main.py",
    ROOT / "branding.py",
    ROOT / "migration_state.py",
    ROOT / "salon_settings.py",
    ROOT / "auth.py",
    ROOT / "dashboard.py",
    ROOT / "billing.py",
    ROOT / "customers.py",
    ROOT / "staff.py",
    ROOT / "inventory.py",
    ROOT / "expenses.py",
    ROOT / "reports.py",
    ROOT / "closing_report.py",
    ROOT / "cloud_sync.py",
]


def main() -> int:
    errors: list[str] = []
    checked: list[str] = []
    for module in MODULES:
        checked.append(module.name)
        try:
            source = module.read_text(encoding="utf-8", errors="replace")
            compile(source, str(module), "exec")
        except Exception as exc:
            errors.append(f"{module.name}: {exc}")

    print(json.dumps({
        "checked_modules": checked,
        "errors": errors,
        "ok": not errors,
    }, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
