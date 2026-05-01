"""Conservative keyboard shortcut support for desktop productivity.

The service is intentionally small in Phase 3. It only handles safe text
shortcuts globally and leaves module-specific row actions for later phases.
"""

from __future__ import annotations

from .clipboard_service import ContextMenuClipboardService, clipboard_service
from .constants import CommonActionId
from .widget_capability_service import WidgetCapabilityService, widget_capability_service


class ContextMenuShortcutService:
    """Install safe app-level shortcuts without replacing screen handlers."""

    TEXT_BIND_TAG = "ContextMenuShortcutText"

    SHORTCUT_LABELS = {
        CommonActionId.COPY: "Ctrl+C",
        CommonActionId.PASTE: "Ctrl+V",
        CommonActionId.CUT: "Ctrl+X",
        CommonActionId.SELECT_ALL: "Ctrl+A",
        CommonActionId.REFRESH: "F5",
        CommonActionId.PRINT: "Ctrl+P",
        CommonActionId.EXPORT: "Ctrl+Shift+E",
        CommonActionId.DELETE: "Delete",
        CommonActionId.OPEN: "Enter",
    }

    def __init__(
        self,
        clipboard: ContextMenuClipboardService | None = None,
        capabilities: WidgetCapabilityService | None = None,
    ):
        self.clipboard = clipboard or clipboard_service
        self.capabilities = capabilities or widget_capability_service
        self.enabled = False
        self.app_ref = None
        self._installed_root_ids: set[int] = set()

    def install(self, root, app_ref=None, enabled: bool = True) -> bool:
        """Install shortcut bindings once for a Tk root.

        Returns True when new bindings were installed. Returning False means
        the root already had this service installed.
        """

        root_id = id(root)
        self.app_ref = app_ref
        self.enabled = bool(enabled)
        if root_id in self._installed_root_ids:
            return False

        self._installed_root_ids.add(root_id)
        self._bind_text_shortcuts(root)
        root.bind_all("<FocusIn>", self._on_focus_in, add="+")
        root.bind_all("<F5>", self._on_refresh, add="+")

        try:
            focused = root.focus_get()
            if focused is not None:
                self._install_text_bind_tag(focused)
        except Exception:
            pass
        return True

    def get_shortcut_label(self, action_id: str) -> str:
        return self.SHORTCUT_LABELS.get(action_id, "")

    def get_basic_shortcuts(self) -> dict[str, str]:
        return dict(self.SHORTCUT_LABELS)

    def _bind_text_shortcuts(self, root) -> None:
        root.bind_class(self.TEXT_BIND_TAG, "<Control-c>", self._on_copy)
        root.bind_class(self.TEXT_BIND_TAG, "<Control-C>", self._on_copy)
        root.bind_class(self.TEXT_BIND_TAG, "<Control-v>", self._on_paste)
        root.bind_class(self.TEXT_BIND_TAG, "<Control-V>", self._on_paste)
        root.bind_class(self.TEXT_BIND_TAG, "<Control-x>", self._on_cut)
        root.bind_class(self.TEXT_BIND_TAG, "<Control-X>", self._on_cut)
        root.bind_class(self.TEXT_BIND_TAG, "<Control-a>", self._on_select_all)
        root.bind_class(self.TEXT_BIND_TAG, "<Control-A>", self._on_select_all)

    def _on_focus_in(self, event):
        if not self.enabled:
            return None
        self._install_text_bind_tag(self._event_widget(event))
        return None

    def _on_copy(self, event):
        widget = self._event_widget(event)
        if not self.enabled or not self._can_copy_or_select(widget):
            return None
        return "break" if self.clipboard.copy_selection(widget) else None

    def _on_paste(self, event):
        widget = self._event_widget(event)
        if not self.enabled or not self.capabilities.is_editable_text_widget(widget):
            return None
        return "break" if self.clipboard.paste_text(widget) else None

    def _on_cut(self, event):
        widget = self._event_widget(event)
        if not self.enabled or not self.capabilities.is_editable_text_widget(widget):
            return None
        return "break" if self.clipboard.cut_selection(widget) else None

    def _on_select_all(self, event):
        widget = self._event_widget(event)
        if not self.enabled or not self._can_copy_or_select(widget):
            return None
        return "break" if self.clipboard.select_all(widget) else None

    def _on_refresh(self, _event):
        if not self.enabled:
            return None

        page_key = str(getattr(self.app_ref, "current_page_key", "") or "").strip().lower()
        if page_key == "billing":
            # Billing already owns F5 for print. Do not change that behavior.
            return None

        frame = None
        try:
            frame = getattr(self.app_ref, "frames", {}).get(page_key)
        except Exception:
            frame = None
        if frame is None or not hasattr(frame, "refresh"):
            return None

        try:
            frame.refresh()
            return "break"
        except Exception:
            return None

    def _install_text_bind_tag(self, widget) -> None:
        if widget is None or not self._is_text_widget(widget):
            return
        try:
            tags = tuple(widget.bindtags())
            if tags and tags[0] == self.TEXT_BIND_TAG:
                return
            filtered = tuple(tag for tag in tags if tag != self.TEXT_BIND_TAG)
            widget.bindtags((self.TEXT_BIND_TAG,) + filtered)
        except Exception:
            pass

    def _is_text_widget(self, widget) -> bool:
        return (
            self.capabilities.is_editable_text_widget(widget)
            or self.capabilities.is_readonly_text_widget(widget)
        )

    def _can_copy_or_select(self, widget) -> bool:
        if widget is None:
            return False
        return self._is_text_widget(widget) and self.capabilities.supports_selection(widget)

    def _event_widget(self, event):
        try:
            return event.widget
        except Exception:
            return None


shortcut_service = ContextMenuShortcutService()
