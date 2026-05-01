import hashlib
import os
import platform
import re
import subprocess
import winreg

DEVICE_SALT = "BOBYS_V5_DEVICE_SALT_2026"


def _normalize(value: str) -> str:
    text = (value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def _machine_guid() -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return _normalize(str(value))
    except Exception:
        return ""


def _processor_id() -> str:
    return _normalize(os.environ.get("PROCESSOR_IDENTIFIER", ""))


def _volume_serial() -> str:
    try:
        drive = os.environ.get("SystemDrive", "C:")
        result = subprocess.run(["cmd", "/c", "vol", drive], capture_output=True, text=True, timeout=5)
        text = (result.stdout or "") + (result.stderr or "")
        return _normalize(text)
    except Exception:
        return ""


def build_device_id() -> str:
    parts = [
        DEVICE_SALT,
        _machine_guid(),
        _volume_serial(),
        _normalize(os.environ.get("COMPUTERNAME", "")),
        _processor_id(),
        _normalize(platform.system()),
        _normalize(platform.release()),
    ]
    raw = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest().upper()
