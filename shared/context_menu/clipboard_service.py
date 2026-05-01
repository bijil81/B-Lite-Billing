"""Clipboard helpers shared by context menus and future shortcuts."""

from __future__ import annotations


class ContextMenuClipboardService:
    def copy_text(self, widget, text: str) -> bool:
        try:
            root = widget.winfo_toplevel() if widget is not None else None
            if root is None:
                return False
            root.clipboard_clear()
            root.clipboard_append(str(text or ""))
            root.update_idletasks()
            return True
        except Exception:
            return False

    def get_selected_text(self, widget) -> str:
        try:
            return str(widget.selection_get())
        except Exception:
            pass
        try:
            start = widget.index("sel.first")
            end = widget.index("sel.last")
            return str(widget.get(start, end))
        except Exception:
            return ""

    def copy_selection(self, widget) -> bool:
        text = self.get_selected_text(widget)
        if not text:
            try:
                text = str(widget.get())
            except Exception:
                text = ""
        return self.copy_text(widget, text)

    def paste_text(self, widget) -> bool:
        try:
            text = widget.winfo_toplevel().clipboard_get()
        except Exception:
            return False
        if not text:
            return True
        try:
            if hasattr(widget, "selection_present") and widget.selection_present():
                start = widget.index("sel.first")
                end = widget.index("sel.last")
                widget.delete(start, end)
                widget.insert(start, text)
            else:
                widget.insert(widget.index("insert"), text)
            return True
        except Exception:
            return False

    def cut_selection(self, widget) -> bool:
        text = self.get_selected_text(widget)
        if not text or not self.copy_text(widget, text):
            return False
        try:
            start = widget.index("sel.first")
            end = widget.index("sel.last")
            widget.delete(start, end)
            return True
        except Exception:
            return False

    def select_all(self, widget) -> bool:
        try:
            widget.focus_set()
            if hasattr(widget, "selection_range"):
                widget.selection_range(0, "end")
                try:
                    widget.icursor("end")
                except Exception:
                    pass
                return True
            widget.tag_add("sel", "1.0", "end")
            return True
        except Exception:
            return False

    def copy_all(self, widget) -> bool:
        try:
            text = widget.get("1.0", "end-1c")
        except Exception:
            try:
                text = widget.get()
            except Exception:
                text = ""
        return self.copy_text(widget, text)


clipboard_service = ContextMenuClipboardService()
