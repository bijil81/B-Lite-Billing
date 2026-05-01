from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from branding import get_build_branding


def _q(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main() -> int:
    info = get_build_branding()
    app_icon_name = Path(info["app_icon"]).name
    installer_icon_name = Path(info["installer_icon"]).name
    runtime_dir_name = info["install_dir_name"]
    appdata_dir_name = f'{runtime_dir_name}_Data'
    env_path = ROOT / "branding_env.cmd"
    nsh_path = ROOT / "branding_build.nsh"

    env_path.write_text(
        "\n".join(
            [
                "@echo off",
                f'set "WL_APP_NAME={info["app_name"]}"',
                f'set "WL_APP_VERSION={info["app_version"]}"',
                f'set "WL_APP_PUBLISHER={info["publisher_name"]}"',
                f'set "WL_EXE_NAME={info["exe_name"]}"',
                f'set "WL_EXE_FILE={info["exe_file"]}"',
                f'set "WL_DIST_NAME={info["dist_name"]}"',
                f'set "WL_INSTALL_DIR_NAME={info["install_dir_name"]}"',
                f'set "WL_INSTALLER_NAME={info["installer_name"]}"',
                f'set "WL_APP_ICON={info["app_icon"]}"',
                f'set "WL_APP_ICON_NAME={app_icon_name}"',
                f'set "WL_INSTALLER_ICON={info["installer_icon"]}"',
                f'set "WL_INSTALLER_ICON_NAME={installer_icon_name}"',
                f'set "WL_RUNTIME_DIR_NAME={runtime_dir_name}"',
                f'set "WL_APPDATA_DIR_NAME={appdata_dir_name}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    nsh_path.write_text(
        "\n".join(
            [
                f'!define WL_APP_NAME "{_q(info["app_name"])}"',
                f'!define WL_APP_VERSION "{_q(info["app_version"])}"',
                f'!define WL_APP_PUBLISHER "{_q(info["publisher_name"])}"',
                f'!define WL_APP_EXE "{_q(info["exe_file"])}"',
                f'!define WL_DIST_DIR "{_q(info["dist_name"])}"',
                f'!define WL_INSTALL_DIR_NAME "{_q(info["install_dir_name"])}"',
                f'!define WL_INSTALLER_OUTFILE "{_q(info["installer_name"])}"',
                f'!define WL_APP_ICON "{_q(info["app_icon"])}"',
                f'!define WL_APP_ICON_NAME "{_q(app_icon_name)}"',
                f'!define WL_INSTALLER_ICON "{_q(info["installer_icon"])}"',
                f'!define WL_INSTALLER_ICON_NAME "{_q(installer_icon_name)}"',
                f'!define WL_RUNTIME_DIR_NAME "{_q(runtime_dir_name)}"',
                f'!define WL_APPDATA_DIR_NAME "{_q(appdata_dir_name)}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Branding applied for {info['app_name']} v{info['app_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
