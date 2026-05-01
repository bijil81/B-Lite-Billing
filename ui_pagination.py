# -*- coding: utf-8 -*-
"""
ui_pagination.py - Phase 3B paginated Treeview rendering helper.

Usage:
  class CustomersFrame(tk.Frame):
      def __init__(self, ...):
          self._pager = TablePager(
              tree=self.tree,
              page_size=50,
              columns=("Name", "Phone", "Visits", "Points", "Total Spent", "Last Visit"),
          )

      def refresh(self):
          rows = self._fetch_all_rows()
          self._pager.render(
              rows=rows,
              value_transform=lambda r: (*r,),  # optional formatting
              summary=f"Showing {self._pager.display_count()} of {len(rows)}",
          )
"""
import tkinter as tk
from tkinter import ttk


class TablePager:
    """Paginated Treeview renderer.

    Shows `page_size` rows at a time with prev/next navigation.
    Eliminates Treeview.insert() overload on large datasets by
    only inserting the visible window.

    Phase 3B FIX: prevents UI freeze on modules with 1000+ rows.
    Phase 5.6.1 Phase 2: adds search result count display.
    """

    PAGE_SIZES = (25, 50, 100, 200)

    def __init__(self, tree: ttk.Treeview, page_size: int = 50,
                 parent: tk.Frame | None = None):
        self.tree = tree
        self.page_size = page_size
        self.page = 0
        self.total_rows = 0
        self.parent = parent

        # Navigation controls (built once, show on demand)
        if parent is not None:
            self._nav_frame = tk.Frame(parent, bg=C["bg"])
            self._prev_btn = tk.Button(
                self._nav_frame, text="< Prev",
                command=self.prev_page, bg=C["sidebar"], fg=C["text"],
                font=("Arial", 10), bd=0, relief="flat", cursor="hand2")
            self._page_label = tk.Label(
                self._nav_frame, text="Page 1",
                bg=C["bg"], fg=C["muted"], font=("Arial", 10))
            self._next_btn = tk.Button(
                self._nav_frame, text="Next >",
                command=self.next_page, bg=C["sidebar"], fg=C["text"],
                font=("Arial", 10), bd=0, relief="flat", cursor="hand2")
            self._size_var = tk.IntVar(value=page_size)
            self._size_combo = ttk.Combobox(
                self._nav_frame, textvariable=self._size_var,
                values=self.PAGE_SIZES, width=4, state="readonly",
                font=("Arial", 10))
            self._size_combo.bind(
                "<<ComboboxSelected>>", lambda e: self._on_size_change())
            # Phase 5.6.1 Phase 2: search result count label
            self._result_count_label = tk.Label(
                self._nav_frame, text="",
                bg=C["bg"], fg=C["muted"], font=("Arial", 10))

    def _build_nav(self):
        if getattr(self, "_nav_frame", None) is None:
            return
        for w in self._nav_frame.winfo_children():
            w.pack_forget()
        self._nav_frame.pack(fill=tk.X)
        self._prev_btn.pack(side=tk.LEFT, padx=4)
        self._page_label.pack(side=tk.LEFT, padx=4)
        self._next_btn.pack(side=tk.LEFT, padx=4)
        self._result_count_label.pack(side=tk.LEFT, padx=8)
        self._size_combo.pack(side=tk.RIGHT, padx=4)

    def _teardown_nav(self):
        if getattr(self, "_nav_frame", None) is None:
            return
        self._nav_frame.pack_forget()

    def display_count(self) -> int:
        return len(self.tree.get_children())

    def render(self, rows: list, *,
               value_transform=None,
               summary: str = "",
               show_nav: bool = True):
        """Clear treeview and render only the current page.

        Args:
            rows: full dataset (all rows that match current filters)
            value_transform: optional callable(row) -> tuple for display
            summary: text appended to page label (e.g. customer count)
            show_nav: whether to show pagination controls
        """
        from utils import C
        self.total_rows = len(rows)
        max_page = max(0, (self.total_rows - 1) // self.page_size)
        self.page = min(self.page, max_page)

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Slice visible window
        start = self.page * self.page_size
        end = start + self.page_size
        page_slice = rows[start:end]

        if value_transform:
            page_slice = [value_transform(r) for r in page_slice]

        for val in page_slice:
            self.tree.insert("", tk.END, values=val)

        # Update nav
        if show_nav:
            self._build_nav()
            actual_page = self.page + 1
            max_pages = max(1, max_page + 1)
            page_text = f"Page {actual_page}/{max_pages}"
            if summary:
                page_text += f"  ({summary})"
            self._page_label.config(text=page_text)
            # Phase 5.6.1 Phase 2: visible result count label
            visible = len(page_slice)
            filtered = len(rows)
            if filtered > 0:
                count_text = f"Showing {visible} of {filtered} result{'s' if filtered != 1 else ''}"
            else:
                count_text = "No results found"
            self._result_count_label.config(text=count_text)
            self._prev_btn.config(state="normal" if self.page > 0 else "disabled")
            self._next_btn.config(state="normal" if self.page < max_page else "disabled")
        else:
            self._teardown_nav()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._render_from_last_rows()

    def next_page(self):
        max_page = max(0, (self.total_rows - 1) // self.page_size)
        if self.page < max_page:
            self.page += 1
            self._render_from_last_rows()

    def _on_size_change(self):
        new_size = self._size_var.get()
        if new_size != self.page_size:
            self.page_size = new_size
            self.page = 0
            self._render_from_last_rows()

    def _render_from_last_rows(self):
        """Re-render using the same rows that were last rendered.

        Stores rows in _last_rows so prev/next can re-access them
        without re-querying.
        """
        if hasattr(self, "_last_rows"):
            self.render(rows=self._last_rows, show_nav=True)

    def render_with_cache(self, rows: list, *,
                          value_transform=None,
                          summary: str = "",
                          show_nav: bool = True):
        """Same as render() but caches rows for prev/next navigation."""
        self._last_rows = rows
        self.render(rows=rows, value_transform=value_transform,
                    summary=summary, show_nav=show_nav)
