# -*- coding: utf-8 -*-
"""
loading_indicator.py - Lightweight loading status indicators.

Phase 5.6.1 Phase 2: non-blocking loading indicators for slow operations.

Usage:
    # As a context manager:
    with LoadingIndicator(self, "Loading customers..."):
        self.load_customers()

    # As a decorator / manual:
    self._loader = LoadingIndicator(parent_frame, "Generating report...")
    self._loader.show()
    do_work()
    self._loader.hide()
"""
import tkinter as tk
from tkinter import ttk
import threading


class LoadingIndicator:
    """Lightweight loading indicator that shows a status label with spinner.

    Does not block the UI thread; uses after() for animated dots.
    """

    def __init__(self, parent: tk.Widget | None, initial_text: str = "Loading..."):
        self.parent = parent
        self.initial_text = initial_text
        self.frame = None
        self.label = None
        self.progress = None
        self._running = False
        self._dot_count = 0
        self._after_id = None

    def show(self):
        """Show the loading indicator (non-blocking)."""
        if not self.parent:
            return
        self._running = True
        self._dot_count = 0

        # Create indicator frame below parent
        self.frame = tk.Frame(self.parent, bg=self._get_bg_color())
        self.frame.pack(side=tk.TOP, fill=tk.X, pady=2)

        self.label = tk.Label(
            self.frame, text=f"{self.initial_text}  ",
            bg=self._get_bg_color(), fg="#6b7280",
            font=("Arial", 10, "italic")
        )
        self.label.pack(side=tk.LEFT, padx=4)

        self.progress = ttk.Progressbar(
            self.frame, mode="indeterminate", length=120
        )
        self.progress.pack(side=tk.RIGHT, padx=4)
        self.progress.start(8)

        # Animate dots
        self._animate_dots()

    def hide(self):
        """Hide the loading indicator."""
        self._running = False
        if self._after_id:
            try:
                self.parent.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self.progress:
            try:
                self.progress.stop()
            except Exception:
                pass
        if self.frame:
            self.frame.destroy()
            self.frame = None
        self.label = None
        self.progress = None

    def update_text(self, text: str):
        """Update loading text while indicator is shown."""
        if self.label:
            self.label.config(text=f"{text}  ")

    def _animate_dots(self):
        if not self._running or not self.label:
            return
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        try:
            self.label.config(text=f"{self.initial_text}{dots}  ")
            self._after_id = self.parent.after(500, self._animate_dots)
        except Exception:
            pass

    def _get_bg_color(self):
        try:
            return self.parent.cget("bg")
        except Exception:
            return "#1a1a2e"

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.hide()
        return False
