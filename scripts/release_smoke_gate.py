from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
PYTEST_TARGETS = [
    "tests/test_billing_logic.py",
    "tests/test_billing_actions.py",
    "tests/test_billing_actions_ui_smoke.py",
    "tests/test_billing_cart_operations.py",
    "tests/test_billing_discounts.py",
    "tests/test_billing_totals.py",
    "tests/test_billing_ui_build_smoke.py",
    "tests/test_billing_whatsapp_actions.py",
    "tests/test_google_backup_tokens.py",
    "tests/test_licensing_admin_keygen.py",
    "tests/test_licensing_security.py",
    "tests/test_main_final_integration_smoke.py",
    "tests/test_packaging_hygiene.py",
    "tests/test_reports_final_integration_smoke.py",
    "tests/test_schema_constraint_migration.py",
    "tests/test_settings_backup_license_about.py",
    "tests/test_settings_core_theme.py",
    "tests/test_settings_security_prefs_notifications.py",
    "tests/test_v56_qa_fixes_ported.py",
    "tests/test_whatsapp_helper_detection.py",
]


def _pytest_command() -> list[str]:
    current_python = [sys.executable, "-m", "pytest"]
    try:
        subprocess.run(
            [sys.executable, "-c", "import pytest"],
            capture_output=True,
            text=True,
            check=True,
        )
        return current_python
    except Exception:
        pass

    if os.name == "nt":
        try:
            probe = subprocess.run(
                ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                check=True,
            )
            python_path = probe.stdout.strip()
            if python_path:
                return ["py", "-3.12", "-m", "pytest"]
        except Exception:
            pass
    return current_python


def main() -> int:
    pytest_cmd = _pytest_command()
    existing_targets = [target for target in PYTEST_TARGETS if (ROOT / target).exists()]
    missing_targets = [target for target in PYTEST_TARGETS if not (ROOT / target).exists()]

    if not existing_targets:
        summary = {
            "pytest_targets": PYTEST_TARGETS,
            "missing_targets": missing_targets,
            "pytest_command": pytest_cmd,
            "returncode": 4,
            "ok": False,
        }
        print(json.dumps(summary, indent=2))
        return 4

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    temp_root = ROOT / ".build-cache" / f"release-smoke-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    temp_root.mkdir(parents=True, exist_ok=True)
    basetemp = temp_root / "basetemp"

    command = [
        *pytest_cmd,
        "-q",
        "-p",
        "no:cacheprovider",
        f"--basetemp={basetemp}",
        *existing_targets,
    ]
    result = subprocess.run(command, cwd=ROOT, env=env)
    summary = {
        "pytest_targets": existing_targets,
        "missing_targets": missing_targets,
        "pytest_command": command[: len(pytest_cmd)],
        "returncode": result.returncode,
        "ok": result.returncode == 0,
    }
    print(json.dumps(summary, indent=2))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
