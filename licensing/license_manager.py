import hashlib
import json
import os
import sys
from .device import build_device_id
from .install import ensure_install_state, mark_startup_and_detect_rollback
from .storage import load_record, save_record
from .trial import trial_status
from .crypto import decode_signed_key, validate_key
from .integrity import verify_critical_files, refresh_critical_file_baseline, current_executable_signature

LICENSE_FILE = "license.dat"


def _build_license_record(payload, raw_key):
    return {
        "kind": payload.get("kind", ""),
        "device_id": payload.get("device_id", ""),
        "install_id": payload.get("install_id", ""),
        "token_hash": hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
        "license_token": raw_key,
    }


def _verify_license_record(record):
    if not record or "license_token" not in record:
        return False, {}
    ok, _, payload = decode_signed_key(record.get("license_token", ""))
    if not ok:
        return False, {}
    return True, payload


class LicenseManager:
    def __init__(self):
        self.device_id = build_device_id()
        self.install_state = ensure_install_state()
        self.install_id = self.install_state["install_id"]
        self.license_record = self._load_verified_license()

    def _load_verified_license(self):
        raw = load_record(LICENSE_FILE)
        ok, payload = _verify_license_record(raw)
        if not ok:
            return {}
        return payload

    def refresh(self):
        self.install_state = ensure_install_state()
        self.install_id = self.install_state["install_id"]
        self.license_record = self._load_verified_license()
        return self

    def register_startup(self):
        self.install_state = ensure_install_state()
        rollback = mark_startup_and_detect_rollback(self.install_state)
        source_mode = (not getattr(sys, "frozen", False)
                       and os.environ.get("BOBYS_V5_ENFORCE_SOURCE_INTEGRITY", "0") != "1")
        exe_sig = current_executable_signature()
        if source_mode and self.install_state.get("code_tamper_detected"):
            self.install_state["code_tamper_detected"] = False
            self.install_state["integrity_executable_signature"] = exe_sig
            save_record("install.dat", self.install_state)
        else:
            stored_sig = self.install_state.get("integrity_executable_signature", "")
            code_tamper = verify_critical_files()
            if code_tamper:
                # Allow one safe baseline refresh when a legitimate packaged build changes.
                if getattr(sys, "frozen", False) and stored_sig != exe_sig:
                    refresh_critical_file_baseline()
                    self.install_state["code_tamper_detected"] = False
                    self.install_state["integrity_executable_signature"] = exe_sig
                    save_record("install.dat", self.install_state)
                else:
                    self.install_state["code_tamper_detected"] = True
                    self.install_state["integrity_executable_signature"] = exe_sig
                    save_record("install.dat", self.install_state)
            else:
                if self.install_state.get("code_tamper_detected") or stored_sig != exe_sig:
                    self.install_state["code_tamper_detected"] = False
                    self.install_state["integrity_executable_signature"] = exe_sig
                    save_record("install.dat", self.install_state)
        return rollback

    def activation_disabled(self):
        return bool(self.install_state.get("date_tamper_detected") or self.install_state.get("code_tamper_detected"))

    def is_activated(self):
        record = self._load_verified_license()
        if not record:
            return False
        return (
            record.get("kind") == "activation"
            and record.get("device_id") == self.device_id
            and record.get("install_id") == self.install_id
        )

    def current_status(self):
        self.refresh()
        t = trial_status(self.install_state)
        activated = self.is_activated()
        if activated:
            t.update({
                "days_left": "Lifetime",
                "expired": False,
                "reminder_required": False,
                "extension_available": False,
            })
        return {
            "device_id": self.device_id,
            "install_id": self.install_id,
            "activated": activated,
            "activation_state": self.install_state.get("activation_state", "trial"),
            "date_tamper_detected": bool(self.install_state.get("date_tamper_detected")),
            "code_tamper_detected": bool(self.install_state.get("code_tamper_detected")),
            "activation_disabled": self.activation_disabled(),
            **t,
        }

    def apply_activation_key(self, raw_key: str):
        if self.activation_disabled():
            return False, "activation_disabled"
        ok, reason = validate_key(raw_key, "activation", self.device_id, self.install_id, 0)
        if not ok:
            return False, reason
        payload = {
            "kind": "activation",
            "device_id": self.device_id,
            "install_id": self.install_id,
            "token_hash": hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
        }
        ok, reason, signed_payload = decode_signed_key(raw_key)
        if not ok:
            return False, reason
        save_record(LICENSE_FILE, _build_license_record(signed_payload, raw_key))
        self.install_state["activation_state"] = "activated"
        self.install_state["activation_applied_utc"] = self.install_state["last_opened_utc"]
        save_record("install.dat", self.install_state)
        return True, "activated"

    def apply_trial_extension_key(self, raw_key: str):
        if self.activation_disabled():
            return False, "activation_disabled"
        if self.install_state.get("trial_extension_used"):
            return False, "already_extended"
        days = int(self.install_state.get("trial_extension_days", 10))
        ok, reason = validate_key(raw_key, "trial_extend", self.device_id, self.install_id, days)
        if not ok:
            return False, reason
        self.install_state["trial_extension_used"] = True
        self.install_state["trial_extended_utc"] = self.install_state["last_opened_utc"]
        save_record("install.dat", self.install_state)
        return True, "trial_extended"


def get_license_manager():
    return LicenseManager()
