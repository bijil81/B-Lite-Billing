"""Settings context menu definitions."""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class SettingsContextAction:
    COPY_BACKUP_FOLDER = "settings.backup.copy_folder"
    COPY_DEVICE_ID = "settings.license.copy_device_id"
    COPY_INSTALL_ID = "settings.license.copy_install_id"
    OPEN_LICENSE_DIALOG = "settings.license.open_dialog"
    REFRESH_LICENSE = "settings.license.refresh"
    COPY_MANIFEST_URL = "settings.about.copy_manifest_url"
    SAVE_MANIFEST_URL = "settings.about.save_manifest_url"
    CHECK_UPDATES = "settings.about.check_updates"


def _action(action_id: str, label: str, shortcut: str = "", danger: bool = False) -> ContextMenuItemDTO:
    return ContextMenuItemDTO.action_item(
        ContextMenuActionDTO(
            id=action_id,
            label=label,
            callback_key=action_id,
            shortcut=shortcut,
            danger=danger,
        )
    )


def get_backup_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="settings_backup_primary",
            title="Backup",
            items=(
                _action(SettingsContextAction.COPY_BACKUP_FOLDER, "Copy backup folder path"),
            ),
        ),
    )


def get_license_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="settings_license_copy",
            title="Copy",
            items=(
                _action(SettingsContextAction.COPY_DEVICE_ID, "Copy device ID"),
                _action(SettingsContextAction.COPY_INSTALL_ID, "Copy installation ID"),
            ),
        ),
        ContextMenuSectionDTO(
            id="settings_license_actions",
            title="License",
            items=(
                _action(SettingsContextAction.OPEN_LICENSE_DIALOG, "Activate or extend trial"),
                _action(SettingsContextAction.REFRESH_LICENSE, "Refresh license status", "F5"),
            ),
        ),
    )


def get_about_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="settings_about_copy",
            title="Copy",
            items=(
                _action(SettingsContextAction.COPY_MANIFEST_URL, "Copy manifest URL"),
            ),
        ),
        ContextMenuSectionDTO(
            id="settings_about_actions",
            title="Update",
            items=(
                _action(SettingsContextAction.SAVE_MANIFEST_URL, "Save manifest URL"),
                _action(SettingsContextAction.CHECK_UPDATES, "Check for updates"),
            ),
        ),
    )
