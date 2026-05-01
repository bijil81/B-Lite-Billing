from __future__ import annotations

from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from branding import get_appdata_dir_name


def appdata_root() -> Path:
    base = os.getenv("APPDATA") or str(Path.home())
    return Path(base) / get_appdata_dir_name()


def main() -> int:
    root = appdata_root()
    required_dirs = [root, root / "Bills", root / "Backups", root / "Trash"]
    errors = []
    for path in required_dirs:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            errors.append(f"{path}: {exc}")

    print(json.dumps({
        "appdata_root": str(root),
        "checked_dirs": [str(p) for p in required_dirs],
        "errors": errors,
        "ok": not errors,
    }, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
