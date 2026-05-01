"""Shared contextual help popup for app menus."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from help_content import get_help_topic
from utils import C, popup_window
from ui_theme import ModernButton
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready


class HelpPopup(tk.Toplevel):
    def __init__(self, parent, topic_key: str):
        super().__init__(parent)
        hide_while_building(self)
        topic = get_help_topic(topic_key)
        self.title(topic["title"])
        self.configure(bg=C["bg"])
        popup_window(self, 700, 560)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        header = tk.Frame(self, bg=C["sidebar"], padx=18, pady=12)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=topic["title"],
            bg=C["sidebar"],
            fg=C["text"],
            font=("Arial", 14, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header,
            text=topic["summary"],
            bg=C["sidebar"],
            fg=C["muted"],
            font=("Arial", 10),
            wraplength=500,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        body = tk.Frame(self, bg=C["bg"], padx=12, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(
            body,
            bg=C["bg"],
            bd=0,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=C["bg"], padx=10, pady=8)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._scroll_widgets = [canvas, scroll_frame]

        for section in topic.get("sections", []):
            heading = tk.Label(
                scroll_frame,
                text=section.get("heading", "Guide"),
                bg=C["bg"],
                fg=C["text"],
                font=("Arial", 12, "bold"),
                anchor="w",
            )
            heading.pack(anchor="w", pady=(4, 8))
            self._scroll_widgets.append(heading)

            for item in section.get("items", []):
                item_label = tk.Label(
                    scroll_frame,
                    text=f"- {item}",
                    bg=C["bg"],
                    fg=C["muted"],
                    font=("Arial", 11),
                    justify="left",
                    wraplength=620,
                    anchor="w",
                )
                item_label.pack(anchor="w", pady=3)
                self._scroll_widgets.append(item_label)

            divider = tk.Frame(scroll_frame, bg=C["card"], height=1, width=620)
            divider.pack(anchor="w", fill=tk.X, pady=(8, 12))
            self._scroll_widgets.append(divider)

        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        for widget in self._scroll_widgets:
            widget.bind("<MouseWheel>", _on_mousewheel)

        footer = tk.Frame(self, bg=C["bg"], padx=18, pady=10)
        footer.pack(fill=tk.X)
        ModernButton(
            footer,
            text="Close",
            command=self._close,
            color=C["blue"],
            hover_color="#154360",
            width=120,
            height=34,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.RIGHT)
        reveal_when_ready(self)

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def show_context_help(parent, topic_key: str):
    return HelpPopup(parent, topic_key)
