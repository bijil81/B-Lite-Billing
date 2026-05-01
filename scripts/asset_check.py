from __future__ import annotations

from pathlib import Path
import json


REQUIRED_FILES = [
    "main.py",
    "WhiteLabelApp.spec",
    "WhiteLabelInstaller.nsi",
    "services_db.json",
    "print_settings.json",
    "pkg_templates.json",
    "membership_templates.json",
    "offers_templates.json",
    "redeem_codes_templates.json",
    "assets",
    "sql",
]


def _branding_asset_ok(root: Path) -> bool:
    branding_logo_dir = root / "assets" / "branding" / "logo"
    branding_icon_dir = root / "assets" / "branding" / "icon"
    logo_candidates = [
        branding_logo_dir / "logo.png",
        branding_logo_dir / "company_logo.png",
        root / "logo.png",
    ]
    icon_candidates = [
        branding_icon_dir / "icon.ico",
        branding_icon_dir / "app.ico",
        branding_icon_dir / "installer.ico",
        root / "icon.ico",
    ]
    splash_candidates = [
        branding_logo_dir / "loading_logo.gif",
        branding_logo_dir / "logo.png",
        root / "loading_logo.gif",
        root / "logo.png",
    ]
    has_logo = any(path.exists() for path in logo_candidates)
    has_icon = any(path.exists() for path in icon_candidates) or any(
        path.is_file() and path.suffix.lower() == ".ico"
        for path in branding_icon_dir.glob("*")
    )
    has_splash = any(path.exists() for path in splash_candidates) or has_logo
    return has_logo and has_icon and has_splash


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [rel for rel in REQUIRED_FILES if not (root / rel).exists()]
    if not _branding_asset_ok(root):
        missing.extend([
            "branding logo asset",
            "branding icon asset",
            "branding splash/logo asset",
        ])
    print(json.dumps({
        "root": str(root),
        "missing_assets": missing,
        "ok": not missing,
    }, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
