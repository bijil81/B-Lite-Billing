"""Cloud sync context menu definitions."""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class CloudSyncContextAction:
    COPY_SYNC_FOLDER = "cloud_sync.folder.copy_path"
    SYNC_NOW = "cloud_sync.folder.sync_now"
    REFRESH_SYNC = "cloud_sync.folder.refresh"
    COPY_SYNC_LOG_SELECTION = "cloud_sync.log.copy_selection"
    COPY_SYNC_LOG_ALL = "cloud_sync.log.copy_all"
    SELECT_SYNC_LOG_ALL = "cloud_sync.log.select_all"
    COPY_OFFLINE_FOLDER = "cloud_sync.offline.copy_path"
    BACKUP_NOW = "cloud_sync.offline.backup_now"
    REFRESH_OFFLINE = "cloud_sync.offline.refresh"
    COPY_OFFLINE_LOG_SELECTION = "cloud_sync.offline_log.copy_selection"
    COPY_OFFLINE_LOG_ALL = "cloud_sync.offline_log.copy_all"
    SELECT_OFFLINE_LOG_ALL = "cloud_sync.offline_log.select_all"
    COPY_VIEWER_URL = "cloud_sync.viewer.copy_url"
    RUN_CONNECTION_CHECK = "cloud_sync.viewer.run_connection_check"


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


def get_sync_folder_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="cloud_sync_folder_copy",
            title="Folder Sync",
            items=(
                _action(CloudSyncContextAction.COPY_SYNC_FOLDER, "Copy sync folder path"),
                _action(CloudSyncContextAction.SYNC_NOW, "Sync now"),
                _action(CloudSyncContextAction.REFRESH_SYNC, "Refresh sync status", "F5"),
            ),
        ),
    )


def get_sync_log_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="cloud_sync_log_copy",
            title="Sync Log",
            items=(
                _action(CloudSyncContextAction.COPY_SYNC_LOG_SELECTION, "Copy selected log text"),
                _action(CloudSyncContextAction.COPY_SYNC_LOG_ALL, "Copy entire sync log"),
                _action(CloudSyncContextAction.SELECT_SYNC_LOG_ALL, "Select all"),
            ),
        ),
    )


def get_offline_backup_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="cloud_sync_offline_actions",
            title="Offline Backup",
            items=(
                _action(CloudSyncContextAction.COPY_OFFLINE_FOLDER, "Copy offline backup path"),
                _action(CloudSyncContextAction.BACKUP_NOW, "Backup now"),
                _action(CloudSyncContextAction.REFRESH_OFFLINE, "Refresh offline status", "F5"),
            ),
        ),
    )


def get_offline_log_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="cloud_sync_offline_log_copy",
            title="Backup Log",
            items=(
                _action(CloudSyncContextAction.COPY_OFFLINE_LOG_SELECTION, "Copy selected log text"),
                _action(CloudSyncContextAction.COPY_OFFLINE_LOG_ALL, "Copy entire backup log"),
                _action(CloudSyncContextAction.SELECT_OFFLINE_LOG_ALL, "Select all"),
            ),
        ),
    )


def get_lan_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="cloud_sync_lan_actions",
            title="Mobile Viewer",
            items=(
                _action(CloudSyncContextAction.COPY_VIEWER_URL, "Copy viewer URL"),
                _action(CloudSyncContextAction.RUN_CONNECTION_CHECK, "Run connection check"),
            ),
        ),
    )
