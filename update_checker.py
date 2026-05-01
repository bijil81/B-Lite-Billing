"""
update_checker.py  -  Lightweight update checker for B-Lite Management

Checks a configurable URL (file path or HTTP endpoint) for a version
manifest JSON. If the remote version is higher than the current one,
offers to open the download page.

Design:
  - No hardcoded server — URL is read from salon_settings.json
  - Non-blocking: runs in a background thread, shows result via after()
  - Graceful degradation: if no URL configured or network fails, silent
  - Manual check available via Settings > About
"""

import threading

try:
    import json
except Exception:
    json = None

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    URLIB_AVAILABLE = True
except Exception:
    URLIB_AVAILABLE = False

from branding import get_branding_value


class UpdateChecker:
    """Check for updates from a manifest URL."""

    # Expected manifest format:
    # {"version": "5.7", "release_date": "2026-04-01",
    #  "changelog": "Bug fixes and improvements",
    #  "download_url": "https://example.com/download"}

    def __init__(self, settings_getter=None):
        self._get_settings = settings_getter
        self._callbacks = []

    def on_update_available(self, callback):
        """Register callback(info_dict). Called when update found."""
        self._callbacks.append(callback)

    def _current_version(self):
        return str(get_branding_value("product_version", "5.6")).strip()

    def _manifest_url(self):
        try:
            if self._get_settings:
                return self._get_settings().get("update_manifest_url", "")
        except Exception:
            pass
        return ""

    def _parse_version(self, ver_str):
        try:
            return tuple(int(x) for x in str(ver_str).split(".") if x.isdigit())
        except Exception:
            return (0,)

    def is_update_available(self, info):
        if not info:
            return False
        return self._parse_version(info.get("version", "0")) > self._parse_version(self._current_version())

    def check_async(self):
        """Run check in background thread, never blocks UI."""
        def _run():
            info = self.check_sync()
            if self.is_update_available(info):
                for cb in self._callbacks:
                    try:
                        cb(info)
                    except Exception:
                        pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def check_sync(self):
        """Synchronous check. Returns dict or None."""
        url = self._manifest_url()
        if not url or not URLIB_AVAILABLE:
            return None

        # Support file:// URLs for local testing
        if url.startswith("file://"):
            return self._check_local(url[7:])

        return self._check_http(url)

    def _check_local(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._validate_manifest(data)
        except Exception:
            return None

    def _check_http(self, url):
        try:
            req = Request(url, headers={"User-Agent": f"BLiteUpdater/{self._current_version()}"})
            resp = urlopen(req, timeout=5)
            data = json.loads(resp.read().decode("utf-8"))
            return self._validate_manifest(data)
        except Exception:
            return None

    def _validate_manifest(self, data):
        if not isinstance(data, dict):
            return None
        version = str(data.get("version", "")).strip()
        if not version:
            return None
        return {
            "version": version,
            "release_date": data.get("release_date", ""),
            "changelog": data.get("changelog", ""),
            "download_url": data.get("download_url", ""),
        }
