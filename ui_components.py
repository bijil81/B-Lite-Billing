"""
ui_components.py  –  BOBY'S Salon : Reusable UI Components
============================================================
High-level UI blocks built on ui_theme.py.
Import: from ui_components import SearchBar, SectionFrame, StatCard, ...

DO NOT put business logic here — UI only.
"""
import tkinter as tk
from tkinter import ttk
from utils import C
from ui_theme import (
    SPACING, BODY_FONT, SMALL_FONT, HEADER_FONT,
    TITLE_FONT, INPUT_FONT, BUTTON_FONT,
    primary_button, secondary_button, danger_button, ghost_button,
    styled_entry, apply_combobox_style, apply_treeview_style,
    add_hover, separator, muted_label,
)


# ─────────────────────────────────────────────────────────
#  1. SEARCH BAR
# ─────────────────────────────────────────────────────────

class SearchBar(tk.Frame):
    """
    Styled search bar with icon, clear button, optional callback.

    Usage:
        bar = SearchBar(parent, placeholder="Search customers...",
                        on_change=lambda q: self._filter(q))
        bar.pack(fill=tk.X, padx=16, pady=8)
        query = bar.get()       # get current text
        bar.clear()             # clear text
    """

    def __init__(self, parent,
                 placeholder: str = "Search...",
                 on_change=None,
                 width: int = 28,
                 bg: str = None,
                 **kwargs):
        bg = bg or C["bg"]
        super().__init__(parent, bg=bg, **kwargs)

        self._on_change = on_change
        self._placeholder = placeholder
        self._has_focus = False

        # Icon label
        tk.Label(self, text="🔍", bg=bg,
                 fg=C["muted"], font=("Arial", 12)).pack(side=tk.LEFT,
                                                          padx=(0, SPACING["xs"]))

        # Entry
        self.var = tk.StringVar()
        self.entry = tk.Entry(
            self,
            textvariable     = self.var,
            font             = INPUT_FONT,
            bg               = C["input"],
            fg               = C["muted"],   # placeholder color
            insertbackground = C["accent"],
            relief           = "flat",
            bd               = 0,
            width            = width,
            highlightthickness= 1,
            highlightcolor   = C["teal"],
            highlightbackground = C["input"],
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                        ipady=SPACING["xs"])
        self._show_placeholder()

        # Clear button
        self._clear_btn = tk.Label(
            self, text="✕", bg=C["input"],
            fg=C["muted"], font=SMALL_FONT,
            cursor="hand2", padx=SPACING["xs"],
        )
        self._clear_btn.pack(side=tk.LEFT)
        self._clear_btn.bind("<Button-1>", lambda e: self.clear())

        # Bindings
        self.entry.bind("<FocusIn>",    self._on_focus_in)
        self.entry.bind("<FocusOut>",   self._on_focus_out)
        self.var.trace("w",             self._on_text_change)

    def _show_placeholder(self):
        if not self.var.get():
            self.entry.configure(fg=C["muted"])
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self._placeholder)
            self._has_focus = False

    def _on_focus_in(self, e=None):
        if not self._has_focus and self.entry.get() == self._placeholder:
            self.entry.delete(0, tk.END)
            self.entry.configure(fg=C["text"])
            self._has_focus = True

    def _on_focus_out(self, e=None):
        if not self.entry.get():
            self._show_placeholder()

    def _on_text_change(self, *args):
        txt = self.var.get()
        is_placeholder = (txt == self._placeholder and not self._has_focus)
        if self._on_change and not is_placeholder:
            try:
                self._on_change(txt)
            except Exception:
                pass
        # Show/hide clear button
        if txt and txt != self._placeholder:
            self._clear_btn.configure(fg=C["text"])
        else:
            self._clear_btn.configure(fg=C["muted"])

    def get(self) -> str:
        """Return current search text (empty string if placeholder)."""
        txt = self.var.get()
        return "" if txt == self._placeholder else txt

    def set(self, text: str):
        """Set search text programmatically."""
        self._has_focus = True
        self.var.set(text)
        self.entry.configure(fg=C["text"])

    def clear(self):
        """Clear search and restore placeholder."""
        self.var.set("")
        self._has_focus = False
        self._show_placeholder()
        if self._on_change:
            try:
                self._on_change("")
            except Exception:
                pass

    def focus(self):
        """Give focus to the search entry."""
        self.entry.focus_set()
        self._on_focus_in()


# ─────────────────────────────────────────────────────────
#  2. SECTION FRAME
# ─────────────────────────────────────────────────────────

class SectionFrame(tk.LabelFrame):
    """
    Titled section frame — consistent section headers.

    Usage:
        sec = SectionFrame(parent, title="Customer", icon="👤")
        sec.pack(fill=tk.X, padx=16, pady=6)
        # Add widgets to sec.body:
        tk.Label(sec.body, text="Name:").pack()
    """

    def __init__(self, parent,
                 title: str,
                 icon: str = "",
                 bg: str = None,
                 body_padx: int = SPACING["md"],
                 body_pady: int = SPACING["sm"],
                 **kwargs):
        bg = bg or C["card"]
        lbl = f" {icon}  {title} " if icon else f" {title} "
        super().__init__(
            parent,
            text   = lbl,
            bg     = bg,
            fg     = C["accent"],
            font   = ("Arial", 11, "bold"),
            bd     = 1,
            relief = "groove",
            **kwargs,
        )
        # Inner content frame
        self.body = tk.Frame(self, bg=bg,
                             padx=body_padx, pady=body_pady)
        self.body.pack(fill=tk.BOTH, expand=True)


# ─────────────────────────────────────────────────────────
#  3. STAT CARD
# ─────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    """
    Dashboard stat card — value + label + optional icon.

    Usage:
        card = StatCard(parent, label="Today Revenue",
                        value="₹12,500", color=C["teal"])
        card.pack(side=tk.LEFT, padx=(0, 8))
        card.update_value("₹15,000")   # update later
    """

    def __init__(self, parent,
                 label: str,
                 value: str = "—",
                 color: str = None,
                 icon: str = "",
                 min_width: int = 120,
                 **kwargs):
        color = color or C["teal"]
        super().__init__(parent,
                         bg    = color,
                         padx  = SPACING["lg"],
                         pady  = SPACING["sm"],
                         **kwargs)
        self._color = color
        self.configure(width=min_width)

        if icon:
            tk.Label(self, text=icon, bg=color,
                     fg="white", font=("Arial", 16)).pack()

        self._val_lbl = tk.Label(
            self, text=value,
            font = ("Arial", 13, "bold"),
            bg   = color, fg = "white",
        )
        self._val_lbl.pack()

        tk.Label(
            self, text=label,
            font = SMALL_FONT,
            bg   = color, fg = "white",
        ).pack()

    def update_value(self, value: str):
        """Update the displayed value."""
        self._val_lbl.configure(text=value)


# ─────────────────────────────────────────────────────────
#  4. EMPTY STATE
# ─────────────────────────────────────────────────────────

class EmptyState(tk.Frame):
    """
    Friendly empty-state message for when there's no data.

    Usage:
        empty = EmptyState(parent,
                           icon="📋",
                           title="No customers yet",
                           subtitle="Add your first customer to get started")
        empty.pack(expand=True)
        empty.show()   # show
        empty.hide()   # hide
    """

    def __init__(self, parent,
                 icon: str = "📋",
                 title: str = "No data",
                 subtitle: str = "",
                 bg: str = None,
                 **kwargs):
        bg = bg or C["bg"]
        super().__init__(parent, bg=bg, **kwargs)

        # Center content
        inner = tk.Frame(self, bg=bg)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text=icon,
                 font=("Arial", 36),
                 bg=bg, fg=C["muted"]).pack(pady=(0, SPACING["sm"]))

        tk.Label(inner, text=title,
                 font=HEADER_FONT,
                 bg=bg, fg=C["muted"]).pack()

        if subtitle:
            tk.Label(inner, text=subtitle,
                     font=SMALL_FONT,
                     bg=bg, fg=C["muted"],
                     wraplength=280,
                     justify="center").pack(pady=(SPACING["xs"], 0))

    def show(self):
        self.lift()

    def hide(self):
        self.lower()


# ─────────────────────────────────────────────────────────
#  5. ACTION BUTTON ROW
# ─────────────────────────────────────────────────────────

class ActionButtonRow(tk.Frame):
    """
    Horizontal row of action buttons with consistent spacing.

    Usage:
        row = ActionButtonRow(parent)
        row.pack(fill=tk.X, padx=16, pady=8)
        row.add_primary("Save", on_save)
        row.add_danger("Delete", on_delete)
        row.add_secondary("Export", on_export)
        row.add_right(tk.Button(...))   # right-aligned button
    """

    def __init__(self, parent, bg: str = None, **kwargs):
        bg = bg or C["bg"]
        super().__init__(parent, bg=bg, **kwargs)
        self._bg = bg

        # Left side (primary actions)
        self._left = tk.Frame(self, bg=bg)
        self._left.pack(side=tk.LEFT)

        # Right side (secondary/utility actions)
        self._right = tk.Frame(self, bg=bg)
        self._right.pack(side=tk.RIGHT)

    def add_primary(self, text: str, command,
                    padx: int = SPACING["md"]) -> tk.Button:
        btn = primary_button(self._left, text, command)
        btn.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        return btn

    def add_secondary(self, text: str, command) -> tk.Button:
        btn = secondary_button(self._left, text, command)
        btn.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        return btn

    def add_danger(self, text: str, command) -> tk.Button:
        btn = danger_button(self._left, text, command)
        btn.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        return btn

    def add_ghost(self, text: str, command) -> tk.Button:
        btn = ghost_button(self._left, text, command, bg=self._bg)
        btn.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        return btn

    def add_right(self, widget: tk.Widget):
        """Add a widget to the right side of the row."""
        widget.pack(in_=self._right, side=tk.RIGHT,
                    padx=(SPACING["sm"], 0))

    def add_right_primary(self, text: str, command) -> tk.Button:
        btn = primary_button(self._right, text, command)
        btn.pack(side=tk.RIGHT, padx=(SPACING["sm"], 0))
        return btn

    def add_right_danger(self, text: str, command) -> tk.Button:
        btn = danger_button(self._right, text, command)
        btn.pack(side=tk.RIGHT, padx=(SPACING["sm"], 0))
        return btn


# ─────────────────────────────────────────────────────────
#  6. STYLED TABLE (Treeview wrapper)
# ─────────────────────────────────────────────────────────

class StyledTable(tk.Frame):
    """
    Dark-theme Treeview wrapper with scrollbar, alternating rows,
    consistent column setup, and selection highlight.

    Usage:
        table = StyledTable(parent,
            columns=[
                {"key":"Name",  "width":160, "anchor":"w"},
                {"key":"Phone", "width":110, "anchor":"w"},
                {"key":"Total", "width":100, "anchor":"e"},
            ],
            height=15,
        )
        table.pack(fill=tk.BOTH, expand=True, padx=16)

        # Insert rows
        table.insert(("Akku", "9876543210", "₹5,000"))
        table.insert(("Bijil","9847523353",  "₹2,000"), tags=("alt",))

        # Bind selection
        table.tree.bind("<<TreeviewSelect>>", on_select)

        # Clear all rows
        table.clear()

        # Get selected row values
        vals = table.selected_values()
    """

    def __init__(self, parent,
                 columns: list,
                 height: int = 15,
                 style_name: str = "Salon.Treeview",
                 show_scrollbar: bool = True,
                 on_double_click=None,
                 **kwargs):
        bg = kwargs.pop("bg", C["bg"])
        super().__init__(parent, bg=bg, **kwargs)

        apply_treeview_style(style_name, row_height=26)

        col_keys = [c["key"] for c in columns]
        self.tree = ttk.Treeview(
            self,
            columns = col_keys,
            show    = "headings",
            height  = height,
            style   = style_name,
        )

        # Configure columns
        for col in columns:
            key    = col["key"]
            width  = col.get("width", 120)
            anchor = col.get("anchor", "w")
            minw   = col.get("minwidth", 40)
            self.tree.heading(key, text=key, anchor=anchor)
            self.tree.column(key, width=width,
                             anchor=anchor, minwidth=minw)

        # Alternating row colors
        self.tree.tag_configure("odd",  background=C["card"])
        self.tree.tag_configure("even", background="#1a1a30")
        self.tree.tag_configure("alt",  background="#1e1e32")

        # Status tags
        self.tree.tag_configure("success", foreground=C["green"])
        self.tree.tag_configure("warning", foreground=C["gold"])
        self.tree.tag_configure("danger",  foreground=C["red"])
        self.tree.tag_configure("muted",   foreground=C["muted"])

        # Scrollbar
        if show_scrollbar:
            vsb = ttk.Scrollbar(self, orient="vertical",
                                command=self.tree.yview)
            self.tree.configure(yscrollcommand=vsb.set)
            self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.LEFT, fill=tk.Y)
        else:
            self.tree.pack(fill=tk.BOTH, expand=True)

        if on_double_click:
            self.tree.bind("<Double-1>",
                           lambda e: on_double_click())

        self._row_count = 0

    def insert(self, values: tuple,
               tags: tuple = None,
               iid: str = None):
        """
        Insert a row. Auto-applies zebra striping.
        tags: additional tags like ("success",) or ("danger",)
        """
        zebra = "odd" if self._row_count % 2 == 0 else "even"
        all_tags = (zebra,) + (tags or ())
        kw = {"values": values, "tags": all_tags}
        if iid:
            kw["iid"] = iid
        self.tree.insert("", tk.END, **kw)
        self._row_count += 1

    def clear(self):
        """Remove all rows."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_count = 0

    def selected_values(self) -> tuple:
        """Return values of the selected row, or empty tuple."""
        sel = self.tree.selection()
        if not sel:
            return ()
        return self.tree.item(sel[0], "values")

    def selected_iid(self) -> str:
        """Return iid of selected row, or empty string."""
        sel = self.tree.selection()
        return sel[0] if sel else ""

    def set_columns(self, columns: list):
        """Reconfigure columns at runtime."""
        for col in columns:
            key    = col["key"]
            width  = col.get("width", 120)
            anchor = col.get("anchor", "w")
            try:
                self.tree.heading(key, text=key, anchor=anchor)
                self.tree.column(key, width=width, anchor=anchor)
            except Exception:
                pass

    def sort_by(self, col: str, reverse: bool = False):
        """Sort table by column."""
        try:
            data = [(self.tree.set(k, col), k)
                    for k in self.tree.get_children("")]
            data.sort(reverse=reverse)
            for idx, (_, k) in enumerate(data):
                self.tree.move(k, "", idx)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
#  CONVENIENCE: HEADER BAR
# ─────────────────────────────────────────────────────────

class HeaderBar(tk.Frame):
    """
    Top header bar with title + optional right-side button.

    Usage:
        hdr = HeaderBar(parent, title="Customers", icon="👥")
        hdr.pack(fill=tk.X)
        hdr.add_button("+ Add", on_add, color=C["teal"])
    """

    def __init__(self, parent,
                 title: str,
                 icon: str = "",
                 bg: str = None,
                 **kwargs):
        bg = bg or C["card"]
        super().__init__(parent, bg=bg, pady=SPACING["sm"], **kwargs)

        lbl_text = f"{icon}  {title}" if icon else title
        tk.Label(self, text=lbl_text,
                 font=TITLE_FONT,
                 bg=bg, fg=C["text"]).pack(side=tk.LEFT,
                                            padx=SPACING["xl"])

        # Right slot for buttons
        self._right = tk.Frame(self, bg=bg)
        self._right.pack(side=tk.RIGHT, padx=SPACING["md"])

    def add_button(self, text: str, command,
                   color: str = None) -> tk.Button:
        color = color or C["teal"]
        btn = tk.Button(
            self._right,
            text    = text,
            command = command,
            bg      = color,
            fg      = "white",
            font    = BUTTON_FONT,
            bd      = 0,
            padx    = SPACING["md"],
            pady    = SPACING["xs"] + 2,
            cursor  = "hand2",
            relief  = "flat",
        )
        btn.pack(side=tk.RIGHT, padx=(SPACING["sm"], 0))
        add_hover(btn, color, C["sidebar"])
        return btn


# ─────────────────────────────────────────────────────────
#  CONVENIENCE: FILTER BAR
# ─────────────────────────────────────────────────────────

class FilterBar(tk.Frame):
    """
    Horizontal filter bar — search + date range + quick buttons.

    Usage:
        bar = FilterBar(parent)
        bar.pack(fill=tk.X, padx=16, pady=4)
        bar.add_search(on_change=self._filter)
        bar.add_button("Today",    self._today,    C["teal"])
        bar.add_button("This Month", self._month,  C["blue"])
    """

    def __init__(self, parent, bg: str = None, **kwargs):
        bg = bg or C["bg"]
        super().__init__(parent, bg=bg, pady=SPACING["xs"], **kwargs)
        self._bg = bg

    def add_search(self, placeholder: str = "Search...",
                   on_change=None,
                   width: int = 22) -> SearchBar:
        bar = SearchBar(self, placeholder=placeholder,
                        on_change=on_change,
                        width=width, bg=self._bg)
        bar.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        return bar

    def add_label(self, text: str) -> tk.Label:
        lbl = tk.Label(self, text=text, bg=self._bg,
                       fg=C["muted"], font=BODY_FONT)
        lbl.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))
        return lbl

    def add_entry(self, textvariable=None,
                  width: int = 13) -> tk.Entry:
        e = styled_entry(self, textvariable=textvariable,
                         width=width)
        e.pack(side=tk.LEFT, ipady=SPACING["xs"],
               padx=(0, SPACING["sm"]))
        return e

    def add_combobox(self, textvariable=None,
                     values=None,
                     width: int = 16) -> ttk.Combobox:
        style_name = apply_combobox_style(self)
        cb = ttk.Combobox(self, textvariable=textvariable,
                          values=values or [],
                          state="readonly",
                          font=BODY_FONT,
                          width=width,
                          style=style_name)
        cb.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        return cb

    def add_button(self, text: str, command,
                   color: str = None) -> tk.Button:
        color = color or C["sidebar"]
        btn = tk.Button(
            self, text=text, command=command,
            bg=color, fg="white",
            font=("Arial", 11, "bold"),
            bd=0, padx=SPACING["sm"], pady=SPACING["xs"]+2,
            cursor="hand2", relief="flat",
        )
        btn.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))
        add_hover(btn, color, C["bg"])
        return btn
