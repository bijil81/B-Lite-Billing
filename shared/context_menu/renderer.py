"""Tkinter renderer for context menu DTOs."""

from __future__ import annotations

from collections.abc import Iterable

from .action_adapter import ContextMenuActionAdapter, action_adapter as default_action_adapter
from .constants import MenuKind
from .dto import ContextMenuContextDTO, ContextMenuItemDTO, ContextMenuSectionDTO
from .feature_flags import is_enabled
from .permission_service import ContextMenuPermissionService, permission_service as default_permission_service
from .styles import get_menu_style


class ContextMenuRendererService:
    def __init__(
        self,
        action_adapter: ContextMenuActionAdapter | None = None,
        permission_service: ContextMenuPermissionService | None = None,
    ) -> None:
        self.action_adapter = action_adapter or default_action_adapter
        self.permission_service = permission_service or default_permission_service

    def build_menu(self, parent, sections: Iterable[ContextMenuSectionDTO], context: ContextMenuContextDTO):
        import tkinter as tk

        menu = tk.Menu(parent, tearoff=0)
        style = get_menu_style()
        try:
            menu.configure(
                background=style["background"],
                foreground=style["foreground"],
                activebackground=style["active_background"],
                activeforeground=style["active_foreground"],
                disabledforeground=style["disabled_foreground"],
            )
        except Exception:
            pass

        item_count = 0
        for section in sections:
            if section.feature_flag and not is_enabled(section.feature_flag, context.module_name):
                continue
            if section.visible_when and not context.extra.get(section.visible_when):
                continue
            if item_count:
                menu.add_separator()
            for item in section.items:
                item_count += self._add_item(menu, item, context)
        return menu

    def _add_item(self, menu, item: ContextMenuItemDTO, context: ContextMenuContextDTO) -> int:
        if item.kind == MenuKind.SEPARATOR:
            menu.add_separator()
            return 1
        if item.kind == MenuKind.SUBMENU:
            import tkinter as tk

            child_menu = tk.Menu(menu, tearoff=0)
            count = 0
            for child in item.children:
                count += self._add_item(child_menu, child, context)
            if count:
                menu.add_cascade(label=item.label, menu=child_menu)
                return 1
            return 0
        if item.kind != MenuKind.ACTION or item.action is None:
            return 0
        action = item.action
        if action.feature_flag and not is_enabled(action.feature_flag, context.module_name):
            return 0
        if not self.permission_service.is_visible(action, context):
            return 0
        enabled = self.permission_service.is_enabled(action, context)
        options = dict(
            label=action.label,
            state="normal" if enabled else "disabled",
            command=lambda a=action: self.action_adapter.dispatch(context, a),
        )
        if action.shortcut:
            options["accelerator"] = action.shortcut
        menu.add_command(**options)
        return 1


renderer_service = ContextMenuRendererService()
