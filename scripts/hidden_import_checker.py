from __future__ import annotations

from pathlib import Path
import ast
import json
import re


MODULE_SPEC_RE = re.compile(r'"([^"]+)":\s*\("([^"]+)",\s*"([^"]+)"\)')


def parse_dynamic_modules(main_path: Path) -> list[str]:
    text = main_path.read_text(encoding="utf-8", errors="replace")
    return sorted({match.group(2) for match in MODULE_SPEC_RE.finditer(text)})


def parse_hiddenimports(spec_path: Path) -> set[str]:
    text = spec_path.read_text(encoding="utf-8", errors="replace").lstrip("\ufeff")
    tree = ast.parse(text)
    hidden: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "hidden":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                hidden.add(elt.value)
    return hidden


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    dynamic_modules = parse_dynamic_modules(root / "main.py")
    hidden = parse_hiddenimports(root / "WhiteLabelApp.spec")
    missing = [module for module in dynamic_modules if module not in hidden]
    print(json.dumps({
        "dynamic_modules": dynamic_modules,
        "missing_hiddenimports": missing,
        "ok": not missing,
    }, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
