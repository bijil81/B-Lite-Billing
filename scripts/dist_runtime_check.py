from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from branding import get_build_branding
from scripts.runtime_manifest import OPTIONAL_RUNTIME_FEATURES, REQUIRED_RUNTIME_FILES


def main() -> int:
    brand = get_build_branding()
    dist_dir = ROOT / "dist" / brand["dist_name"]
    exe_name = brand["exe_name"]
    if not str(exe_name).lower().endswith(".exe"):
        exe_name = f"{exe_name}.exe"
    exe_path = dist_dir / exe_name
    runtime_dir = dist_dir / "_internal"
    required_paths = {
        "dist_dir": dist_dir,
        "exe_path": exe_path,
        "runtime_dir": runtime_dir,
        "base_library_zip": runtime_dir / "base_library.zip",
        "sql_dir": runtime_dir / "sql",
        "assets_dir": runtime_dir / "assets",
    }
    missing = [name for name, path in required_paths.items() if not path.exists()]
    python_dlls = sorted(path.name for path in runtime_dir.glob("python*.dll")) if runtime_dir.exists() else []
    if not python_dlls:
        missing.append("python_runtime_dll")
    missing_runtime_files = [
        rel_path for rel_path in REQUIRED_RUNTIME_FILES
        if not (runtime_dir / rel_path).exists()
    ]
    missing.extend(f"runtime::{rel_path}" for rel_path in missing_runtime_files)
    optional_runtime_features = {
        feature_name: all((runtime_dir / rel_path).exists() for rel_path in rel_paths)
        for feature_name, rel_paths in OPTIONAL_RUNTIME_FEATURES.items()
    }

    ok = not missing
    print(json.dumps({
        "dist_dir": str(dist_dir),
        "exe_path": str(exe_path),
        "runtime_dir": str(runtime_dir),
        "python_dlls": python_dlls,
        "required_runtime_files": REQUIRED_RUNTIME_FILES,
        "missing_runtime_files": missing_runtime_files,
        "optional_runtime_features": optional_runtime_features,
        "missing": missing,
        "ok": ok,
    }, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
