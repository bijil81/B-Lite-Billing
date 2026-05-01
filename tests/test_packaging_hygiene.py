from __future__ import annotations

from pathlib import Path


def test_pyinstaller_spec_excludes_admin_tests_and_dev_tooling():
    root = Path(__file__).resolve().parents[1]
    spec = (root / "WhiteLabelApp.spec").read_text(encoding="utf-8")

    assert "'licensing_admin'" in spec
    assert "'tests'" in spec
    assert "'pytest'" in spec
    assert "'_pytest'" in spec
    assert "'licensing.public_key'" in spec
    assert "licensing_admin.keygen" not in spec.split("hidden = [", 1)[1].split("]", 1)[0]
    assert "licensing_admin" not in spec.split("datas = [", 1)[1].split("]", 1)[0]
    assert "private_key" not in spec.split("datas = [", 1)[1].split("]", 1)[0]


def test_build_script_runs_dist_runtime_validation():
    root = Path(__file__).resolve().parents[1]
    build_script = (root / "BUILD.bat").read_text(encoding="utf-8")

    assert "scripts\\dist_runtime_check.py" in build_script
    assert "PyInstaller" in build_script
