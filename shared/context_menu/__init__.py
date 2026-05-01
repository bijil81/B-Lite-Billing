"""Shared context menu foundation for B-Lite Management."""

from .dto import (
    ContextMenuActionDTO,
    ContextMenuContextDTO,
    ContextMenuItemDTO,
    ContextMenuSectionDTO,
)
from .feature_flags import is_enabled
from .registry import ContextMenuRegistryService
from .action_adapter import ContextMenuActionAdapter
from .shortcut_service import ContextMenuShortcutService

__all__ = [
    "ContextMenuActionDTO",
    "ContextMenuContextDTO",
    "ContextMenuItemDTO",
    "ContextMenuSectionDTO",
    "is_enabled",
    "ContextMenuRegistryService",
    "ContextMenuActionAdapter",
    "ContextMenuShortcutService",
]
