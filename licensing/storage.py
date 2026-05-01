import json
import os
import winreg
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from branding import get_programdata_dir_name, get_runtime_app_slug

_RUNTIME_ID = get_runtime_app_slug()
PROGRAM_DATA_DIR = rf"C:\ProgramData\{get_programdata_dir_name()}"
LEGACY_PROGRAM_DATA_DIR = r"C:\ProgramData\Bobys"
PUBLIC_BACKUP_FILE = r"C:\Users\Public\Libraries\syscache.dat"
REG_PATH = rf"Software\{_RUNTIME_ID}\Licensing"
LEGACY_REG_PATH = r"Software\Bobys\Licensing"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_storage_dir() -> str:
    os.makedirs(PROGRAM_DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(PUBLIC_BACKUP_FILE), exist_ok=True)
    return PROGRAM_DATA_DIR


def _file_path(name: str, base_dir: str | None = None) -> str:
    return os.path.join(base_dir or ensure_storage_dir(), name)


def _canonical(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _with_signature(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(data)
    payload["updated_at_utc"] = payload.get("updated_at_utc") or _utc_now()
    return payload


def _verify_signature(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    if not data:
        return False, {}
    payload = dict(data)
    payload.pop("__sig", None)
    return True, payload


def _load_json_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_json_file(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)


def _load_registry(path: str, name: str) -> Dict[str, Any]:
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
        raw, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return json.loads(raw)
    except Exception:
        return {}


def _save_registry(name: str, data: Dict[str, Any]) -> None:
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
    winreg.SetValueEx(key, name, 0, winreg.REG_SZ, json.dumps(data, sort_keys=True))
    winreg.CloseKey(key)


def _public_backup_key(name: str) -> str:
    return f"public::{name}"


def _sources_for(name: str) -> List[Tuple[str, Dict[str, Any]]]:
    sources = [
        ("programdata", _load_json_file(_file_path(name, PROGRAM_DATA_DIR))),
        ("programdata_legacy", _load_json_file(_file_path(name, LEGACY_PROGRAM_DATA_DIR))),
        ("public", _load_json_file(PUBLIC_BACKUP_FILE if name == "install.dat" else "")),
        ("registry", _load_registry(REG_PATH, name)),
        ("registry_legacy", _load_registry(LEGACY_REG_PATH, name)),
    ]
    normalized = []
    for source_name, raw in sources:
        if not raw:
            continue
        if source_name == "public" and raw.get("record_name") != name:
            continue
        ok, payload = _verify_signature(raw)
        if ok:
            normalized.append((source_name, payload))
    return normalized


def load_record(name: str) -> Dict[str, Any]:
    candidates = _sources_for(name)
    if not candidates:
        return {}
    candidates.sort(key=lambda item: item[1].get("updated_at_utc", ""), reverse=True)
    source_name, payload = candidates[0]
    if source_name in {"programdata_legacy", "registry_legacy"}:
        try:
            save_record(name, payload)
        except Exception:
            pass
    return payload


def save_record(name: str, data: Dict[str, Any]) -> None:
    signed = _with_signature(data)
    try:
        _save_json_file(_file_path(name), signed)
    except Exception:
        pass
    _save_registry(name, signed)
    if name == "install.dat":
        public_data = dict(signed)
        public_data["record_name"] = name
        try:
            _save_json_file(PUBLIC_BACKUP_FILE, public_data)
        except Exception:
            pass


def program_data_path(name: str) -> str:
    return _file_path(name)


def public_backup_path() -> str:
    ensure_storage_dir()
    return PUBLIC_BACKUP_FILE
