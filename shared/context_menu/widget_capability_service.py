"""Widget capability detection for context menu behavior."""

from __future__ import annotations


class WidgetCapabilityService:
    def widget_class_name(self, widget) -> str:
        try:
            return str(widget.winfo_class()).lower()
        except Exception:
            return widget.__class__.__name__.lower()

    def state_value(self, widget) -> str:
        try:
            return str(widget.cget("state") or "").lower()
        except Exception:
            return ""

    def is_editable_text_widget(self, widget) -> bool:
        cls = self.widget_class_name(widget)
        state = self.state_value(widget)
        return cls in {"entry", "text", "spinbox", "tentry"} and state not in {"disabled", "readonly"}

    def is_readonly_text_widget(self, widget) -> bool:
        cls = self.widget_class_name(widget)
        state = self.state_value(widget)
        return cls in {"entry", "text", "spinbox", "tentry"} and state in {"readonly", "disabled"}

    def supports_selection(self, widget) -> bool:
        return any(hasattr(widget, name) for name in ("selection_get", "selection", "curselection", "selection_range"))

    def supports_multiselect(self, widget) -> bool:
        cls = self.widget_class_name(widget)
        if cls in {"treeview", "listbox"}:
            return True
        try:
            mode = str(widget.cget("selectmode") or "").lower()
            return mode in {"extended", "multiple"}
        except Exception:
            return False


widget_capability_service = WidgetCapabilityService()
