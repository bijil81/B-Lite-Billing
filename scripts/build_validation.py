from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "scripts" / "asset_check.py",
    ROOT / "scripts" / "hidden_import_checker.py",
    ROOT / "scripts" / "developer_path_check.py",
    ROOT / "scripts" / "installer_validation.py",
    ROOT / "scripts" / "module_compile_check.py",
    ROOT / "scripts" / "release_smoke_gate.py",
    ROOT / "scripts" / "startup_validation.py",
]


def main() -> int:
    failed = False
    for script in SCRIPTS:
        print(f"[build_validation] running {script.name}")
        result = subprocess.run([sys.executable, str(script)], cwd=ROOT)
        if result.returncode != 0:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
