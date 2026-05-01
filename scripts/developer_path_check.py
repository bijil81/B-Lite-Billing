from __future__ import annotations

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
CHECK_EXTS = {".py", ".bat", ".spec", ".nsi"}
SKIP_PARTS = {
    "build",
    "dist",
    ".pytest_cache",
    "__pycache__",
    ".git",
    ".venv-build",
    ".build-temp",
    ".build-cache",
}
BAD_PATTERNS = (
    r"C:\Users\bijil",
    r"G:\chimmu",
    r"Bobys Billing V3",
)


def should_scan(path: Path) -> bool:
    return path.suffix.lower() in CHECK_EXTS and not any(part in SKIP_PARTS for part in path.parts)


def main() -> int:
    findings: list[dict[str, object]] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pattern in BAD_PATTERNS:
            if pattern in text:
                findings.append({
                    "file": str(path.relative_to(ROOT)),
                    "pattern": pattern,
                })
    print(json.dumps({
        "developer_specific_paths": findings,
        "ok": not findings,
    }, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
