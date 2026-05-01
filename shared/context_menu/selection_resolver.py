"""Selection resolution helpers for common Tk widgets."""

from __future__ import annotations

from typing import Any

from .constants import WidgetType


class ContextMenuSelectionResolver:
    def resolve_widget_type(self, widget) -> str:
        try:
            cls = str(widget.winfo_class()).lower()
        except Exception:
            cls = widget.__class__.__name__.lower()
        if "treeview" in cls:
            return WidgetType.TREEVIEW
        if "listbox" in cls:
            return WidgetType.LISTBOX
        if "text" in cls:
            return WidgetType.TEXT
        if "entry" in cls:
            return WidgetType.ENTRY
        return WidgetType.UNKNOWN

    def selected_text(self, widget) -> str:
        try:
            return str(widget.selection_get())
        except Exception:
            return ""

    def treeview_selection(self, widget, event=None) -> dict[str, Any]:
        row_id = ""
        try:
            if event is not None:
                row_id = str(widget.identify_row(event.y) or "")
        except Exception:
            row_id = ""
        if not row_id:
            try:
                selected = widget.selection()
                row_id = str(selected[0]) if selected else ""
            except Exception:
                row_id = ""
        if not row_id:
            return {}
        try:
            item = widget.item(row_id) or {}
        except Exception:
            item = {}
        return {
            "row_id": row_id,
            "text": item.get("text", ""),
            "values": tuple(item.get("values", ()) or ()),
        }

    def listbox_selection(self, widget) -> dict[str, Any]:
        try:
            indexes = tuple(int(i) for i in widget.curselection())
        except Exception:
            indexes = ()
        values = []
        for index in indexes:
            try:
                values.append(widget.get(index))
            except Exception:
                pass
        return {"indexes": indexes, "values": tuple(values)}

    def resolve(self, widget, event=None) -> dict[str, Any]:
        widget_type = self.resolve_widget_type(widget)
        if widget_type == WidgetType.TREEVIEW:
            row = self.treeview_selection(widget, event)
            return {"widget_type": widget_type, "selected_row": row, "selection_count": 1 if row else 0}
        if widget_type == WidgetType.LISTBOX:
            row = self.listbox_selection(widget)
            return {"widget_type": widget_type, "selected_row": row, "selection_count": len(row.get("indexes", ()))}
        return {
            "widget_type": widget_type,
            "selected_text": self.selected_text(widget),
            "selection_count": 1 if self.selected_text(widget) else 0,
        }


selection_resolver = ContextMenuSelectionResolver()
