import hashlib
import os
import sys
from pathlib import Path
from branding import get_appdata_dir_name, get_programdata_dir_name

ROOT = Path(__file__).resolve().parent.parent
CRITICAL_FILES = [
    ROOT / "main.py",
    ROOT / "salon_settings.py",
    ROOT / "licensing" / "storage.py",
    ROOT / "licensing" / "device.py",
    ROOT / "licensing" / "install.py",
    ROOT / "licensing" / "crypto.py",
    ROOT / "licensing" / "license_manager.py",
    ROOT / "licensing" / "ui_gate.py",
]


def _baseline_candidates():
    if getattr(sys, "frozen", False):
        candidates = [
            Path(os.getenv("PROGRAMDATA", "C:/ProgramData")) / get_programdata_dir_name() / "licensing" / "integrity_baseline.json",
            Path(os.getenv("APPDATA", str(ROOT))) / get_appdata_dir_name() / "licensing" / "integrity_baseline.json",
        ]
    else:
        candidates = [
            Path(__file__).resolve().parent / "integrity_baseline.json",
            ROOT / ".runtime" / "integrity_baseline.json",
        ]
    unique = []
    seen = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def current_critical_digests():
    current = {}
    for path in CRITICAL_FILES:
        if path.exists():
            digest = _sha256(path)
            if digest:
                current[str(path)] = digest
    return current


def current_executable_signature() -> str:
    if not getattr(sys, "frozen", False):
        return "source"
    try:
        exe_path = Path(sys.executable)
        stat = exe_path.stat()
        payload = f"{exe_path}|{stat.st_size}|{int(stat.st_mtime)}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
    except Exception:
        return "frozen-unknown"


def _load_baseline():
    import json

    for baseline_file in _baseline_candidates():
        if not baseline_file.exists():
            continue
        try:
            return json.loads(baseline_file.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def _save_baseline(data):
    import json
    payload = json.dumps(data, indent=2, sort_keys=True)
    for baseline_file in _baseline_candidates():
        try:
            baseline_file.parent.mkdir(parents=True, exist_ok=True)
            baseline_file.write_text(payload, encoding="utf-8")
            return baseline_file
        except (PermissionError, OSError):
            continue
    return None


def verify_critical_files():
    # Avoid false-positive lockouts while the source build is still being actively edited.
    # Real code-tamper enforcement should apply to packaged/frozen builds.
    if not getattr(sys, "frozen", False) and os.environ.get("BOBYS_V5_ENFORCE_SOURCE_INTEGRITY", "0") != "1":
        return False
    current = current_critical_digests()
    baseline = _load_baseline()
    if not baseline:
        _save_baseline(current)
        return False
    for path, digest in baseline.items():
        if current.get(path) != digest:
            return True
    return False



def refresh_critical_file_baseline():
    current = current_critical_digests()
    _save_baseline(current)
    return current
