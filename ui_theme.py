# -*- coding: utf-8 -*-
"""
ui_theme.py - BOBY'S Salon : Centralized UI Design System
=========================================================
Reusable UI helpers for all modules.
Import: from ui_theme import SPACING, primary_button, create_card, ...

DO NOT put business logic here - UI only.

UI v3.0 additions (dark theme preserved, no existing code changed):
  - ModernButton   : rounded canvas button, hover + shadow effect
  - ModernCard     : SaaS-style card with left accent border
  - StatusBadge    : pill-shaped colored status label
  - SectionHeader  : modern page header with icon + divider line
  - ModernEntry    : rounded-look entry with focus ring
  - stat_card_v3   : upgraded stat card with icon + gradient feel
"""
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from utils import C


def _hex_to_rgb(value: str):
    value = (value or "#000000").lstrip("#")
    if len(value) != 6:
        return (0, 0, 0)
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def _is_light_color(value: str) -> bool:
    r, g, b = _hex_to_rgb(value)
    luminance = (0.299 * r) + (0.587 * g) + (0.114 * b)
    return luminance >= 180


def _contrast_text(bg: str, light: str = "#ffffff", dark: str = "#111827") -> str:
    return dark if _is_light_color(bg) else light


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  SPACING SYSTEM
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
SPACING = {
    "xs":  4,
    "sm":  8,
    "md":  12,
    "lg":  16,
    "xl":  24,
    "xxl": 32,
}


def _base_font() -> int:
    """Return the current responsive base font size for ttk widgets."""
    try:
        from ui_responsive import get_current_font_size
        return get_current_font_size()
    except Exception:
        return _FONT_BASE


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  FONT SYSTEM
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
# Phase 3 FIX: Fonts are now computed dynamically from ui_responsive.font_sz.
#
# Strategy: We define them as mutable module-level tuples that get
# recomputed by refresh_fonts() when responsive metrics change. This
# gives us dynamic scaling without breaking existing callers that use
# these as direct references (e.g., font=TITLE_FONT with no parens).
#
# Defaults are used only if ui_responsive hasn't yet run (import-time safety).
_FONT_BASE = 10  # overridden at startup by refresh_fonts()


def _make_font(sz_delta=0, bold=False, family="Arial"):
    """Create a font tuple at (font_sz + delta) from the responsive system."""
    try:
        from ui_responsive import get_current_font_size
        sz = max(8, get_current_font_size() + sz_delta)
    except Exception:
        sz = max(8, _FONT_BASE + sz_delta)  # fallback if responsive not ready
    return (family, sz, "bold") if bold else (family, sz)


TITLE_FONT   = _make_font(5, bold=True)     # Page titles: base+5 bold
HEADER_FONT  = _make_font(3, bold=True)     # Section headers: base+3 bold
BODY_FONT    = _make_font(1)                # General text: base+1
SMALL_FONT   = _make_font(0)                # Labels: base+0
MONO_FONT    = _make_font(0, family="Courier New")  # Code preview
INPUT_FONT   = _make_font(2)                # Entry widgets: base+2
BUTTON_FONT  = _make_font(1, bold=True)     # Buttons: base+1 bold
TAB_FONT     = _make_font(1, bold=True)     # Notebook tabs: base+1 bold


def refresh_fonts():
    """Recompute all font constants from the current responsive font_sz.

    Phase 3 FIX: Call this after initialize_responsive(root) runs.
    This updates the module-level font constants so all downstream
    callers automatically pick up the correct sizes.
    """
    global TITLE_FONT, HEADER_FONT, BODY_FONT, SMALL_FONT
    global MONO_FONT, INPUT_FONT, BUTTON_FONT, TAB_FONT

    TITLE_FONT   = _make_font(5, bold=True)
    HEADER_FONT  = _make_font(3, bold=True)
    BODY_FONT    = _make_font(1)
    SMALL_FONT   = _make_font(0)
    MONO_FONT    = _make_font(0, family="Courier New")
    INPUT_FONT   = _make_font(2)
    BUTTON_FONT  = _make_font(1, bold=True)
    TAB_FONT     = _make_font(1, bold=True)


def ensure_segoe_ttk_font():
    """Apply a consistent ttk font for forms and popup controls.

    Phase 3 FIX: Uses _base_font() for size instead of hardcoded 10,
    so ttk controls scale with the responsive system.
    """
    try:
        families = {name.lower() for name in tkfont.families()}
        base_family = "Segoe UI" if "segoe ui" in families else "Arial"
        base_sz = _base_font()
        base_font = (base_family, base_sz)
        heading_font = (base_family, base_sz, "bold")
        style = ttk.Style()
        style.configure(".", font=base_font)
        style.configure("TNotebook.Tab", font=base_font)
        style.configure("Treeview", font=base_font)
        style.configure("Treeview.Heading", font=heading_font)
        style.configure("TCombobox", font=base_font)
        style.configure("TLabel", font=base_font)
        style.configure("TCheckbutton", font=base_font)
        style.configure("TRadiobutton", font=base_font)
        style.configure("TButton", font=base_font)
    except Exception:
        pass


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  BUTTON FACTORIES
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def primary_button(parent, text, command, **kwargs) -> tk.Button:
    """Teal primary action button."""
    btn = tk.Button(
        parent,
        text      = text,
        command   = command,
        bg        = C["teal"],
        fg        = "white",
        font      = BUTTON_FONT,
        bd        = 0,
        padx      = kwargs.pop("padx", SPACING["lg"]),
        pady      = kwargs.pop("pady", SPACING["sm"]),
        cursor    = "hand2",
        relief    = "flat",
        activebackground = C["green"],
        activeforeground = "white",
        **kwargs,
    )
    _add_hover(btn, C["teal"], C["green"])
    return btn


def secondary_button(parent, text, command, **kwargs) -> tk.Button:
    """Sidebar-colored secondary button."""
    btn = tk.Button(
        parent,
        text      = text,
        command   = command,
        bg        = C["sidebar"],
        fg        = C["text"],
        font      = BUTTON_FONT,
        bd        = 0,
        padx      = kwargs.pop("padx", SPACING["md"]),
        pady      = kwargs.pop("pady", SPACING["sm"]),
        cursor    = "hand2",
        relief    = "flat",
        activebackground = C["bg"],
        activeforeground = C["text"],
        **kwargs,
    )
    _add_hover(btn, C["sidebar"], C["bg"])
    return btn


def danger_button(parent, text, command, **kwargs) -> tk.Button:
    """Red destructive action button."""
    btn = tk.Button(
        parent,
        text      = text,
        command   = command,
        bg        = C["red"],
        fg        = "white",
        font      = BUTTON_FONT,
        bd        = 0,
        padx      = kwargs.pop("padx", SPACING["md"]),
        pady      = kwargs.pop("pady", SPACING["sm"]),
        cursor    = "hand2",
        relief    = "flat",
        activebackground = "#c0392b",
        activeforeground = "white",
        **kwargs,
    )
    _add_hover(btn, C["red"], "#c0392b")
    return btn


def ghost_button(parent, text, command, **kwargs) -> tk.Button:
    """Transparent ghost button — for minor actions."""
    bg = kwargs.pop("bg", C["bg"])
    btn = tk.Button(
        parent,
        text      = text,
        command   = command,
        bg        = bg,
        fg        = C["muted"],
        font      = SMALL_FONT,
        bd        = 0,
        padx      = kwargs.pop("padx", SPACING["sm"]),
        pady      = kwargs.pop("pady", SPACING["xs"]),
        cursor    = "hand2",
        relief    = "flat",
        activebackground = C["input"],
        activeforeground = C["text"],
        **kwargs,
    )
    _add_hover(btn, bg, C["input"], fg_normal=C["muted"], fg_hover=C["text"])
    return btn


def accent_button(parent, text, command, **kwargs) -> tk.Button:
    """Pink accent button — for special highlights."""
    btn = tk.Button(
        parent,
        text      = text,
        command   = command,
        bg        = C["accent"],
        fg        = "white",
        font      = BUTTON_FONT,
        bd        = 0,
        padx      = kwargs.pop("padx", SPACING["lg"]),
        pady      = kwargs.pop("pady", SPACING["sm"]),
        cursor    = "hand2",
        relief    = "flat",
        activebackground = C["purple"],
        activeforeground = "white",
        **kwargs,
    )
    _add_hover(btn, C["accent"], C["purple"])
    return btn


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  CARD CONTAINER
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def create_card(parent, padx: int = SPACING["md"],
                pady: int = SPACING["sm"], **kwargs) -> tk.Frame:
    """
    Rounded-look card frame with card background.
    Usage:
        card = create_card(parent)
        card.pack(fill=tk.X, padx=16, pady=8)
        tk.Label(card, text="Hello").pack()
    """
    return tk.Frame(
        parent,
        bg     = C["card"],
        padx   = padx,
        pady   = pady,
        **kwargs,
    )


def create_section(parent, **kwargs) -> tk.Frame:
    """Slightly darker section frame — for grouping."""
    return tk.Frame(
        parent,
        bg   = C["dark2"] if "dark2" in C else C["card"],
        **kwargs,
    )


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  SECTION TITLE
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def section_title(parent, text: str,
                  icon: str = "",
                  bg: str = None) -> tk.Label:
    """
    Styled section/page title label.
    Usage:
        section_title(frame, "Billing", icon="🧾").pack(anchor="w", padx=16, pady=8)
    """
    bg = bg or C["card"]
    lbl_text = f"{icon}  {text}" if icon else text
    return tk.Label(
        parent,
        text = lbl_text,
        font = HEADER_FONT,
        bg   = bg,
        fg   = C["accent"],
    )


def page_title(parent, text: str,
               icon: str = "",
               bg: str = None) -> tk.Label:
    """Large page-level title."""
    bg = bg or C["card"]
    lbl_text = f"{icon}  {text}" if icon else text
    return tk.Label(
        parent,
        text = lbl_text,
        font = TITLE_FONT,
        bg   = bg,
        fg   = C["text"],
    )


def muted_label(parent, text: str,
                bg: str = None, **kwargs) -> tk.Label:
    """Small muted label — for field labels, hints."""
    bg = bg or C["card"]
    return tk.Label(
        parent,
        text = text,
        font = BODY_FONT,
        bg   = bg,
        fg   = C["muted"],
        **kwargs,
    )


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  INPUT STYLING
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def style_entry(widget: tk.Entry,
                fg: str = None,
                bg: str = None) -> tk.Entry:
    """
    Apply dark-theme styling to an existing Entry widget.
    Usage:
        e = tk.Entry(parent)
        style_entry(e)
        e.pack(...)
    """
    widget.configure(
        bg              = bg or C["input"],
        fg              = fg or C["text"],
        insertbackground= C["accent"],
        relief          = "flat",
        bd              = 0,
        highlightthickness = 1,
        highlightcolor     = C["teal"],
        highlightbackground= C["input"],
        font            = INPUT_FONT,
    )
    return widget


def styled_entry(parent, **kwargs) -> tk.Entry:
    """
    Create a pre-styled Entry widget.
    Usage:
        e = styled_entry(parent, textvariable=var)
        e.pack(fill=tk.X, ipady=6)
    """
    e = tk.Entry(
        parent,
        bg               = kwargs.pop("bg", C["input"]),
        fg               = kwargs.pop("fg", C["text"]),
        insertbackground = C["accent"],
        relief           = "flat",
        bd               = 0,
        highlightthickness= 1,
        highlightcolor   = C["teal"],
        highlightbackground= C["input"],
        font             = kwargs.pop("font", INPUT_FONT),
        **kwargs,
    )
    return e


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  COMBOBOX STYLING — DARK THEME FIX
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def apply_combobox_style(root_or_widget,
                         style_name: str = "Dark.TCombobox") -> str:
    """
    Apply dark-theme compatible combobox style.
    Call once per Toplevel/Frame before creating Combobox widgets.

    Usage:
        style_name = apply_combobox_style(self)
        cb = ttk.Combobox(parent, style=style_name, ...)

    Returns the style name to pass to Combobox(style=...).
    """
    style = ttk.Style()
    style.configure(
        style_name,
        fieldbackground  = C["input"],
        background       = C["input"],
        foreground       = C["text"],
        selectbackground = C["teal"],
        selectforeground = "white",
        arrowcolor       = C["accent"],
        borderwidth      = 0,
        font             = ("Arial", _base_font()),
    )
    style.map(
        style_name,
        fieldbackground = [("readonly", C["input"]),
                           ("disabled", C["sidebar"])],
        foreground      = [("readonly", C["text"]),
                           ("disabled", C["muted"])],
        selectbackground= [("focus", C["teal"])],
    )
    # Dropdown list colors
    cb_list_font = ("Arial", _base_font())
    try:
        root_or_widget.option_add(
            "*TCombobox*Listbox.background",       C["card"])
        root_or_widget.option_add(
            "*TCombobox*Listbox.foreground",       C["text"])
        root_or_widget.option_add(
            "*TCombobox*Listbox.selectBackground", C["teal"])
        root_or_widget.option_add(
            "*TCombobox*Listbox.selectForeground", "white")
        root_or_widget.option_add(
            "*TCombobox*Listbox.font",             cb_list_font)
    except Exception:
        pass

    return style_name


def apply_global_ttk_dark_theme(root) -> None:
    """
    Full Windows-style modern dark mode for ALL ttk widgets.
    Call ONCE in main.py after root + theme colours are ready:

        apply_theme(cfg["theme"])
        apply_global_ttk_dark_theme(root)
        root.update_idletasks()
    """
    style = ttk.Style()
    is_light = _is_light_color(C["bg"])
    tree_bg = "#ffffff" if is_light else C["card"]
    tree_field_bg = "#f8fafc" if is_light else C["card"]
    heading_bg = C["blue"] if is_light else C["sidebar"]
    heading_fg = _contrast_text(heading_bg, light="#ffffff", dark=C["text"])
    selected_bg = C["blue"] if is_light else C["accent"]
    selected_fg = _contrast_text(selected_bg, light="#ffffff", dark=C["text"])
    notebook_tab_bg = "#e5e7eb" if is_light else C["sidebar"]
    notebook_active_bg = "#dbeafe" if is_light else C["bg"]
    combobox_popup_bg = "#ffffff" if is_light else C["input"]
    disabled_bg = "#d1d5db" if is_light else C["sidebar"]
    scrollbar_trough = "#e5e7eb" if is_light else C["bg"]

    # "default" engine — every sub-element is configurable on all platforms
    style.theme_use("default")
    _ttk_base_sz = _base_font()

    # —€—€ Global tk widget defaults (affects ALL tk.* widgets) —€—€—€—€—€—€—€—€—€—€—€—€—€—€
    root.option_add("*Background",          C["bg"])
    root.option_add("*Foreground",          C["text"])
    root.option_add("*Font",                f"Arial {_ttk_base_sz}")
    root.option_add("*Entry.Background",    C["input"])
    root.option_add("*Entry.Foreground",    C["text"])
    root.option_add("*Entry.Relief",        "flat")
    root.option_add("*Text.Background",     C["input"])
    root.option_add("*Text.Foreground",     C["text"])
    root.option_add("*Text.Relief",         "flat")
    root.option_add("*Listbox.Background",  tree_bg)
    root.option_add("*Listbox.Foreground",  C["text"])
    root.option_add("*Listbox.Relief",      "flat")
    root.option_add("*Listbox.BorderWidth", "0")
    root.option_add("*Listbox.SelectBackground", C["teal"])
    root.option_add("*Listbox.SelectForeground", "white")

    # —€—€ Combobox —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TCombobox",
        fieldbackground  = C["input"],
        background       = C["input"],
        foreground       = C["text"],
        selectbackground = C["input"],
        selectforeground = C["text"],
        bordercolor      = C["input"],
        lightcolor       = C["input"],
        darkcolor        = C["input"],
        arrowcolor       = C["text"],
        insertcolor      = C["accent"],
        borderwidth      = 0,
        relief           = "flat",
        padding          = [6, 4],
    )
    style.map(
        "TCombobox",
        fieldbackground = [
            ("readonly",  C["input"]),
            ("!readonly", C["input"]),
              ("disabled",  disabled_bg),
            ("active",    C["input"]),
            ("!disabled", C["input"]),
        ],
        foreground = [
            ("readonly",  C["text"]),
            ("!readonly", C["text"]),
            ("disabled",  C["muted"]),
            ("active",    C["text"]),
        ],
        background = [
            ("readonly",  C["input"]),
            ("active",    C["sidebar"]),
            ("!disabled", C["input"]),
        ],
        bordercolor      = [("focus", C["teal"])],
        lightcolor       = [("focus", C["teal"])],
        darkcolor        = [("focus", C["teal"])],
        arrowcolor       = [("disabled", C["muted"]),
                            ("!disabled", C["text"])],
        selectbackground = [("focus", C["teal"])],
        selectforeground = [("focus", "white")],
    )
    # Dropdown popup Listbox
    root.option_add("*TCombobox*Listbox.Background",       combobox_popup_bg)
    root.option_add("*TCombobox*Listbox.Foreground",       C["text"])
    root.option_add("*TCombobox*Listbox.SelectBackground", C["teal"])
    root.option_add("*TCombobox*Listbox.SelectForeground", "white")
    root.option_add("*TCombobox*Listbox.Font",             ("Arial", _base_font()))
    root.option_add("*TCombobox*Listbox.Relief",           "flat")
    root.option_add("*TCombobox*Listbox.BorderWidth",      "0")

    # —€—€ Entry —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TEntry",
        fieldbackground  = C["input"],
        foreground       = C["text"],
        selectbackground = C["teal"],
        selectforeground = "white",
        insertcolor      = C["accent"],
        bordercolor      = C["input"],
        lightcolor       = C["input"],
        darkcolor        = C["input"],
        borderwidth      = 0,
        relief           = "flat",
        padding          = [6, 4],
    )
    style.map(
        "TEntry",
        fieldbackground = [
            ("disabled",  disabled_bg),
            ("readonly",  C["input"]),
            ("!disabled", C["input"]),
            ("focus",     C["input"]),
        ],
        foreground = [
            ("disabled", C["muted"]),
            ("focus",    C["text"]),
        ],
        bordercolor = [("focus", C["teal"])],
        lightcolor  = [("focus", C["teal"])],
        darkcolor   = [("focus", C["teal"])],
    )

    # —€—€ Notebook —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TNotebook",
        background   = C["bg"],
        borderwidth  = 0,
        tabmargins   = [0, 0, 0, 0],
    )
    style.configure(
        "TNotebook.Tab",
        background   = notebook_tab_bg,
        foreground   = C["muted"],
        borderwidth  = 0,
        padding      = [14, 6],
        font         = TAB_FONT,
        focuscolor   = notebook_tab_bg,
    )
    style.map(
        "TNotebook.Tab",
        background = [("selected", C["card"]),
                      ("active",   notebook_active_bg)],
        foreground = [("selected", C["text"]),
                      ("active",   C["text"])],
        expand     = [("selected", [1, 1, 1, 0])],
    )

    # —€—€ Treeview —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "Treeview",
        background        = tree_bg,
        foreground        = C["text"],
        fieldbackground   = tree_field_bg,
        borderwidth       = 0,
        relief            = "flat",
        rowheight         = max(24, _base_font() + 14),
        font              = ("Arial", _base_font()),
    )
    style.configure(
        "Treeview.Heading",
        background  = heading_bg,
        foreground  = heading_fg,
        relief      = "flat",
        borderwidth = 0,
        font        = ("Arial", _base_font(), "bold"),
    )
    style.map(
        "Treeview",
        background = [("selected", selected_bg)],
        foreground = [("selected", selected_fg)],
    )
    style.map(
        "Treeview.Heading",
        background = [("active", notebook_active_bg)],
        foreground = [("active", heading_fg)],
    )

    # —€—€ Scrollbar —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TScrollbar",
        background   = C["sidebar"],
        troughcolor  = scrollbar_trough,
        arrowcolor   = C["muted"],
        borderwidth  = 0,
        relief       = "flat",
        gripcount    = 0,
    )
    style.map(
        "TScrollbar",
        background = [("active",   C["teal"]),
                      ("disabled", C["bg"])],
        arrowcolor = [("active",   C["text"])],
    )

    # —€—€ Progressbar —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TProgressbar",
        background  = C["teal"],
        troughcolor = C["input"],
        borderwidth = 0,
        relief      = "flat",
    )

    # —€—€ Scale (slider) —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TScale",
        background  = C["bg"],
        troughcolor = C["input"],
        borderwidth = 0,
    )
    style.map(
        "TScale",
        background = [("active", C["teal"])],
    )

    # —€—€ Checkbutton —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TCheckbutton",
        background        = C["bg"],
        foreground        = C["text"],
        focuscolor        = C["bg"],
        indicatorcolor    = C["input"],
        indicatormargin   = [4, 4, 8, 4],
    )
    style.map(
        "TCheckbutton",
        background     = [("active", C["bg"])],
        foreground     = [("disabled", C["muted"])],
        indicatorcolor = [("selected", C["teal"]),
                          ("active",   C["sidebar"])],
    )

    # —€—€ Radiobutton —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TRadiobutton",
        background      = C["bg"],
        foreground      = C["text"],
        focuscolor      = C["bg"],
        indicatorcolor  = C["input"],
    )
    style.map(
        "TRadiobutton",
        background     = [("active", C["bg"])],
        foreground     = [("disabled", C["muted"])],
        indicatorcolor = [("selected", C["teal"]),
                          ("active",   C["sidebar"])],
    )

    # —€—€ Button —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TButton",
        background  = C["sidebar"],
        foreground  = C["text"],
        borderwidth = 0,
        relief      = "flat",
        padding     = [12, 6],
        font        = ("Arial", _ttk_base_sz, "bold"),
        focuscolor  = C["sidebar"],
    )
    style.map(
        "TButton",
        background = [("active",   C["teal"]),
                      ("disabled", C["bg"])],
        foreground = [("disabled", C["muted"])],
    )

    # —€—€ Label —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TLabel",
        background = C["bg"],
        foreground = C["text"],
        font       = ("Arial", _ttk_base_sz),
    )

    # —€—€ Frame / LabelFrame —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TFrame",
        background = C["bg"],
        relief     = "flat",
    )
    style.configure(
        "TLabelframe",
        background  = C["bg"],
        foreground  = C["muted"],
        bordercolor = C["sidebar"],
        relief      = "flat",
        borderwidth = 1,
    )
    style.configure(
        "TLabelframe.Label",
        background = C["bg"],
        foreground = C["muted"],
        font       = ("Arial", 10, "bold"),
    )

    # —€—€ Separator —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TSeparator",
        background = C["sidebar"],
    )

    # —€—€ Spinbox —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    style.configure(
        "TSpinbox",
        fieldbackground = C["input"],
        foreground      = C["text"],
        background      = C["input"],
        bordercolor     = C["input"],
        arrowcolor      = C["text"],
        borderwidth     = 0,
        relief          = "flat",
        padding         = [6, 4],
    )
    style.map(
        "TSpinbox",
        fieldbackground = [("readonly", C["input"]),
                           ("disabled", C["sidebar"])],
        foreground      = [("disabled", C["muted"])],
        bordercolor     = [("focus",    C["teal"])],
    )


def styled_combobox(parent, **kwargs) -> ttk.Combobox:
    """
    Create a pre-styled dark-theme Combobox.
    Usage:
        cb = styled_combobox(parent, textvariable=var, values=[...])
        cb.pack(fill=tk.X)
    """
    style_name = apply_combobox_style(parent)
    return ttk.Combobox(
        parent,
        style  = style_name,
        font   = kwargs.pop("font", ("Arial", 11)),
        **kwargs,
    )


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  HOVER EFFECT HELPER
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def _add_hover(widget: tk.Widget,
               bg_normal:  str,
               bg_hover:   str,
               fg_normal:  str = "white",
               fg_hover:   str = "white"):
    """
    Internal: bind Enter/Leave events for hover color change.
    """
    widget.bind("<Enter>",
                lambda e: widget.configure(bg=bg_hover,   fg=fg_hover),
                add="+")
    widget.bind("<Leave>",
                lambda e: widget.configure(bg=bg_normal,  fg=fg_normal),
                add="+")


def add_hover(widget: tk.Widget,
              bg_normal: str,
              bg_hover:  str,
              fg_normal: str = "white",
              fg_hover:  str = "white"):
    """
    Public: add hover highlight to any tk.Button or tk.Label.
    Usage:
        btn = tk.Button(parent, ...)
        add_hover(btn, C["teal"], C["green"])
    """
    _add_hover(widget, bg_normal, bg_hover, fg_normal, fg_hover)


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  SEPARATOR
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def separator(parent, bg: str = None,
              height: int = 1,
              padx: int = 0) -> tk.Frame:
    """Thin horizontal separator line."""
    return tk.Frame(
        parent,
        bg     = bg or C["muted"],
        height = height,
        padx   = padx,
    )


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  STAT CARD (dashboard cards)
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def stat_card(parent, label: str, value: str,
              color: str = None) -> tk.Frame:
    """
    Small colored stat card — for dashboards, summaries.
    Usage:
        stat_card(frame, "Today Revenue", "₹12,500", C["teal"]).pack(side=tk.LEFT)
    """
    color = color or C["teal"]
    fg = _contrast_text(color, light="#ffffff", dark=C.get("text", "#111827"))
    card = tk.Frame(parent, bg=color, padx=SPACING["lg"], pady=SPACING["sm"])
    tk.Label(card, text=value,
             font=("Arial", 12, "bold"),
             bg=color, fg=fg).pack()
    tk.Label(card, text=label,
             font=SMALL_FONT,
             bg=color, fg=fg).pack()
    return card


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  TREEVIEW STYLE
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€


# ═════════════════════════════════════════════════════════
#  UI v3.0 — MODERN SaaS COMPONENTS
#  Dark theme preserved — additive only, zero existing changes
# ═════════════════════════════════════════════════════════


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  MODERN BUTTON  — rounded canvas, hover, shadow
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

class ModernButton(tk.Frame):
    """
    Stable Frame-based modern button — Python 3.14 compatible.
    No Canvas, no TclError. Hover effect + shadow simulation via
    nested frames. Drop-in replacement for tk.Button.

    Usage:
        ModernButton(parent, text="Save", command=fn,
                     color=C["teal"]).pack(side=tk.LEFT, padx=4)
    """

    def __init__(self, parent, text, command=None,
                 color=None, hover_color=None,
                 text_color=None,
                 width=140, height=36,
                 radius=8,
                 font=None, **kwargs):

        image = kwargs.pop("image", None)
        compound = kwargs.pop("compound", "left")
        anchor = kwargs.pop("anchor", "center")
        justify = kwargs.pop("justify", "center")

        color       = color       or C["teal"]
        hover_color = hover_color or C["blue"]
        font        = font        or ("Arial", 10, "bold")
        text_color  = text_color  or _contrast_text(
            color,
            light="#ffffff",
            dark=C.get("text", "#111827"),
        )
        hover_text_color = _contrast_text(
            hover_color,
            light="#ffffff",
            dark=C.get("text", "#111827"),
        )

        # Outer frame = shadow / border effect (1px darker)
        super().__init__(parent,
                         bg=self._darken(color, 0.65),
                         cursor="hand2")

        # Inner label = the button face
        self._lbl = tk.Label(
            self,
            text=text,
            image=image,
            compound=compound,
            bg=color,
            fg=text_color,
            font=font,
            padx=10,
            pady=max(4, (height - 22) // 2),
            cursor="hand2",
            relief="flat",
            bd=0,
            anchor=anchor,
            justify=justify,
        )
        self._lbl.pack(fill="both",
                       expand=True,
                       padx=1,        # 1px shadow on sides
                       pady=(0, 2))   # 2px shadow on bottom

        self._color = color
        self._hover_color = hover_color
        self._text_color = text_color
        self._hover_text_color = hover_text_color
        self._cmd = command
        self._image = image

        # Hover bindings on both frame and label
        for w in (self, self._lbl):
            w.bind("<Enter>",           self._on_enter)
            w.bind("<Leave>",           self._on_leave)
            w.bind("<ButtonPress-1>",   self._on_press)
            w.bind("<ButtonRelease-1>", self._on_release)

    # —€—€ Color helpers —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    def _darken(self, hex_color, f=0.72):
        try:
            h = hex_color.lstrip("#")
            r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
            return f"#{max(0,int(r*f)):02x}{max(0,int(g*f)):02x}{max(0,int(b*f)):02x}"
        except Exception:
            return hex_color

    # —€—€ Hover / press handlers —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    def _on_enter(self, e=None):
        self._lbl.configure(bg=self._hover_color, fg=self._hover_text_color)
        self.configure(bg=self._darken(self._hover_color, 0.65))

    def _on_leave(self, e=None):
        self._lbl.configure(bg=self._color, fg=self._text_color)
        self.configure(bg=self._darken(self._color, 0.65))

    def _on_press(self, e=None):
        pressed = self._darken(self._hover_color, 0.85)
        self._lbl.configure(
            bg=pressed,
            fg=_contrast_text(pressed, light="#ffffff", dark=C.get("text", "#111827"))
        )
        self.configure(bg=self._darken(pressed, 0.65))

    def _on_release(self, e=None):
        self._on_enter()
        if self._cmd:
            self._cmd()

    # —€—€ Public API to update button dynamically —€—€—€—€—€—€—€—€—€—€
    def set_text(self, text):
        self._lbl.configure(text=text)

    def set_color(self, color, hover_color=None):
        self._color = color
        self._hover_color = hover_color or self._darken(color, 0.8)
        self._text_color = _contrast_text(
            self._color,
            light="#ffffff",
            dark=C.get("text", "#111827"),
        )
        self._hover_text_color = _contrast_text(
            self._hover_color,
            light="#ffffff",
            dark=C.get("text", "#111827"),
        )
        self._on_leave()
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  MODERN CARD  — SaaS card with left accent border
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def modern_card(parent, accent_color=None,
                padx=14, pady=12, **kwargs) -> tk.Frame:
    """
    SaaS-style card — card bg + subtle left colored border.
    Usage:
        card = modern_card(parent, accent_color=C["teal"])
        card.pack(fill=tk.X, padx=16, pady=6)
    """
    accent = accent_color or C["teal"]
    outer  = tk.Frame(parent, bg=accent, padx=2, pady=0)
    inner  = tk.Frame(outer,  bg=C["card"],
                      padx=padx, pady=pady, **kwargs)
    inner.pack(fill=tk.BOTH, expand=True, padx=(3, 0))
    outer._inner = inner          # expose inner for adding children
    return outer


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  STATUS BADGE  — pill-shaped colored status label
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

_BADGE_COLORS = {
    "active":     ("#0ea5e9", "#0c4a6e"),   # sky blue
    "scheduled":  ("#0ea5e9", "#0c4a6e"),
    "completed":  ("#10b981", "#064e3b"),   # green
    "cancelled":  ("#ef4444", "#7f1d1d"),   # red
    "no show":    ("#f59e0b", "#78350f"),   # amber
    "inactive":   ("#64748b", "#1e293b"),   # gray
    "low":        ("#ef4444", "#7f1d1d"),
    "vip":        ("#f59e0b", "#78350f"),
    "owner":      ("#8b5cf6", "#3b0764"),   # purple
    "staff":      ("#0ea5e9", "#0c4a6e"),
}

def status_badge(parent, text: str, bg: str = None) -> tk.Label:
    """
    Pill-shaped colored status badge.
    Auto-picks color based on text if bg not given.
    Usage:
        status_badge(frame, "Completed").pack(side=tk.LEFT)
        status_badge(frame, "VIP", bg=C["gold"]).pack()
    """
    key = text.lower().strip()
    if bg:
        fg = "white"
    else:
        bg, dark = _BADGE_COLORS.get(key, ("#334155", "#0f172a"))
        fg = "white"

    return tk.Label(
        parent,
        text    = f"  {text}  ",
        bg      = bg,
        fg      = fg,
        font    = ("Arial", 9, "bold"),
        relief  = "flat",
        bd      = 0,
        padx    = 4,
        pady    = 2,
    )


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  SECTION HEADER  — modern page/section header
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def section_header(parent, title: str, icon: str = "",
                   subtitle: str = "",
                   btn_text: str = "",
                   btn_command=None,
                   btn_color: str = None) -> tk.Frame:
    """
    Modern SaaS-style section header with optional action button.
    Usage:
        section_header(self, "Customers", icon="👥",
                       btn_text="+ Add", btn_command=self._add).pack(fill=tk.X)
    """
    frm = tk.Frame(parent, bg=C["card"], pady=10)

    left = tk.Frame(frm, bg=C["card"])
    left.pack(side=tk.LEFT, padx=20, fill=tk.Y)

    # Title row
    title_txt = f"{icon}  {title}" if icon else title
    tk.Label(left, text=title_txt,
             font=("Arial", 15, "bold"),
             bg=C["card"], fg=C["text"]).pack(anchor="w")

    # Subtitle (optional)
    if subtitle:
        tk.Label(left, text=subtitle,
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")

    # Action button (optional)
    if btn_text and btn_command:
        ModernButton(
            frm, text=btn_text, command=btn_command,
            color=btn_color or C["teal"],
            hover_color=C["blue"],
            width=148, height=34, radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.RIGHT, padx=15, pady=6)

    return frm


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  MODERN ENTRY  — rounded-look entry with focus ring
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def modern_entry(parent, **kwargs) -> tk.Frame:
    """
    Rounded-look entry — wraps tk.Entry in a styled Frame.
    Returns a Frame; access the Entry via .entry attribute.
    Usage:
        wrap = modern_entry(parent, textvariable=var)
        wrap.pack(fill=tk.X, pady=4)
        # bind to wrap.entry directly if needed
    """
    radius_color = kwargs.pop("border_color", C["teal"])
    bg           = kwargs.pop("bg", C["input"])
    fg           = kwargs.pop("fg", C["text"])
    font         = kwargs.pop("font", ("Arial", 11))
    width        = kwargs.pop("width", None)

    # Outer frame simulates rounded border
    outer = tk.Frame(parent, bg=C["sidebar"], padx=1, pady=1)
    inner = tk.Frame(outer, bg=bg, padx=4, pady=0)
    inner.pack(fill=tk.X, padx=1, pady=1)

    entry_kw = dict(
        bg=bg, fg=fg, font=font,
        insertbackground=C["accent"],
        relief="flat", bd=0,
        highlightthickness=0,
        **kwargs,
    )
    if width:
        entry_kw["width"] = width

    e = tk.Entry(inner, **entry_kw)
    e.pack(fill=tk.X, ipady=5)
    outer.entry = e

    # Focus ring effect
    def _focus_in(ev):
        outer.configure(bg=radius_color)
    def _focus_out(ev):
        outer.configure(bg=C["sidebar"])
    e.bind("<FocusIn>",  _focus_in)
    e.bind("<FocusOut>", _focus_out)

    return outer


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  STAT CARD v3  — premium dashboard stat card
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def stat_card_v3(parent, label: str, value: str,
                 icon: str = "",
                 color: str = None,
                 width: int = 160) -> tk.Frame:
    """
    Premium SaaS stat card with icon, value, label.
    Uses existing C[] colors — dark theme preserved.
    Usage:
        stat_card_v3(frame, "Revenue", "₹12,500",
                     icon="💰", color=C["teal"]).pack(side=tk.LEFT, padx=6)
    """
    color = color or C["teal"]
    dark  = _darken_hex(color, 0.65)

    card = tk.Frame(parent, bg=C["card"],
                    padx=16, pady=12,
                    relief="flat", bd=0)

    # Top row: icon
    if icon:
        icon_f = tk.Frame(card, bg=color,
                          width=32, height=32, padx=4, pady=4)
        icon_f.pack(anchor="w", pady=(0, 6))
        icon_f.pack_propagate(False)
        tk.Label(icon_f, text=icon, bg=color,
                 font=("Arial", 14)).pack(expand=True)

    # Value (large)
    tk.Label(card, text=value,
             font=("Arial", 16, "bold"),
             bg=C["card"], fg=C["text"]).pack(anchor="w")

    # Label (muted)
    tk.Label(card, text=label,
             font=("Arial", 10),
             bg=C["card"], fg=C["muted"]).pack(anchor="w")

    # Bottom accent line
    tk.Frame(card, bg=color, height=3).pack(
        fill=tk.X, side=tk.BOTTOM, pady=(8, 0))

    return card


def _darken_hex(hex_color: str, f: float = 0.75) -> str:
    """Darken a hex color by factor f (internal helper)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return (f"#{max(0,int(r*f)):02x}"
            f"{max(0,int(g*f)):02x}"
            f"{max(0,int(b*f)):02x}")


# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
#  TREEVIEW COLUMN ALIGNMENT  (global standard)
# —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

def apply_treeview_column_alignment(tree) -> None:
    """
    Apply professional alignment to any ttk.Treeview.
    Rule:  Headers â†’ center
           Numbers/amounts â†’ right
           Dates/Status/Phone/Invoice â†’ center
           Text â†’ left

    Usage (after Treeview + columns are created):
        from ui_theme import apply_treeview_column_alignment
        apply_treeview_column_alignment(self.tree)
    """
    NUMBER_KEYS = {
        "qty", "price", "cost", "amount", "total", "value",
        "discount", "wallet", "commission", "revenue", "avg",
        "sales", "count", "earned", "disc%", "disc",
        "commission %", "commission%", "times used", "% of revenue",
    }
    CENTER_KEYS = {
        "date", "time", "status", "expiry", "phone",
        "invoice", "pay", "payment", "active", "✅",
        "valid from", "valid to", "size", "in time", "out time",
    }

    for col in tree["columns"]:
        c = col.lower().strip()

        # Determine alignment based on column type
        if any(k in c for k in NUMBER_KEYS):
            anc = "e"           # numbers  â†’ right
        elif any(k in c for k in CENTER_KEYS):
            anc = "center"      # date/status/phone â†’ center
        else:
            anc = "w"           # text â†’ left

        # Header AND data use same anchor — consistent look
        tree.heading(col, anchor=anc)
        tree.column(col,  anchor=anc)

def apply_treeview_style(style_name: str = "Salon.Treeview",
                         row_height: int = 26) -> str:
    """
    Apply dark-theme Treeview style.
    Usage:
        apply_treeview_style()
        tree = ttk.Treeview(parent, style="Salon.Treeview")

    Returns style name.
    """
    style = ttk.Style()
    is_light = _is_light_color(C["bg"])
    tree_bg = "#ffffff" if is_light else C["card"]
    heading_bg = C["blue"] if is_light else C["sidebar"]
    heading_fg = _contrast_text(heading_bg, light="#ffffff", dark=C["text"])
    selected_bg = C["blue"] if is_light else C["teal"]
    selected_fg = _contrast_text(selected_bg, light="#ffffff", dark=C["text"])
    style.configure(
        style_name,
        background        = tree_bg,
        foreground        = C["text"],
        fieldbackground   = tree_bg,
        rowheight         = row_height,
        font              = ("Arial", 11),
        borderwidth       = 0,
    )
    style.configure(
        f"{style_name}.Heading",
        background        = heading_bg,
        foreground        = heading_fg,
        font              = ("Arial", 11, "bold"),
        relief            = "flat",
    )
    style.map(
        style_name,
        background = [("selected", selected_bg)],
        foreground = [("selected", selected_fg)],
    )
    return style_name


# ═══════════════════════════════════════════════════════════
#  ANIMATION ENGINE
#  Usage: from ui_theme import anim
#         anim.init(root)          # once, after tk.Tk()
#         anim.smooth_drag(div, panel)
#         anim.color(w, "#aaa", "#0ea5e9")
#         anim.count_up(lbl, 0, 11165)
#         anim.pulse(w, C["teal"], C["bg"])
#         anim.shake(entry_widget)
# ═══════════════════════════════════════════════════════════
import time as _time


def _ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3

def _ease_in_out(t: float) -> float:
    return 4*t*t*t if t < 0.5 else 1 - (-2*t+2)**3/2

def _lerp_color(a: str, b: str, t: float) -> str:
    try:
        ah = a.lstrip("#"); bh = b.lstrip("#")
        ar,ag,ab_ = int(ah[0:2],16),int(ah[2:4],16),int(ah[4:6],16)
        br,bg_,bb = int(bh[0:2],16),int(bh[2:4],16),int(bh[4:6],16)
        return "#{:02x}{:02x}{:02x}".format(
            int(ar+(br-ar)*t), int(ag+(bg_-ag)*t), int(ab_+(bb-ab_)*t))
    except Exception:
        return b


class AnimationEngine:
    """60fps animation loop for Tkinter — singleton via `anim`."""

    TICK = 16   # ms per frame (~60fps)

    def __init__(self):
        self._tasks: list = []
        self._root = None
        self._after_id = None

    def init(self, root):
        """Call once: anim.init(self.root) in SalonApp.__init__"""
        if self._after_id and self._root is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
        self._root = root
        self._tick()

    def stop(self):
        self._tasks = []
        if self._after_id and self._root is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
        self._root = None

    def _tick(self):
        if self._root is None:
            self._after_id = None
            return
        now    = _time.perf_counter()
        alive  = []
        for t in self._tasks:
            try:
                elapsed = now - t["t0"]
                raw     = min(1.0, elapsed / t["dur"])
                eased   = t["ease"](raw)
                t["fn"](eased)
                if raw < 1.0:
                    alive.append(t)
                else:
                    t["fn"](1.0)
                    if t.get("done"):
                        t["done"]()
            except Exception:
                pass
        self._tasks = alive
        if self._root:
            try:
                if int(self._root.winfo_exists()):
                    self._after_id = self._root.after(self.TICK, self._tick)
                else:
                    self._after_id = None
            except Exception:
                self._after_id = None
                self._root = None

    def _add(self, fn, dur_ms, ease=None, done=None):
        self._tasks.append({
            "t0":   _time.perf_counter(),
            "dur":  dur_ms / 1000,
            "fn":   fn,
            "ease": ease or _ease_out,
            "done": done,
        })

    # —€—€ Public API —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€

    def color(self, widget, from_hex: str, to_hex: str,
              prop: str = "bg", dur: int = 160):
        """Smooth color transition — hover effects, state changes."""
        def fn(t):
            try:
                widget.configure(**{prop: _lerp_color(from_hex, to_hex, t)})
            except Exception:
                pass
        self._add(fn, dur)

    def width(self, widget, from_w: int, to_w: int,
              dur: int = 220, done=None):
        """Animate widget width — panel expand/collapse."""
        def fn(t):
            try:
                widget.configure(width=int(from_w + (to_w - from_w) * t))
            except Exception:
                pass
        self._add(fn, dur, done=done)

    def count_up(self, label, from_v: float, to_v: float,
                 prefix: str = "", suffix: str = "",
                 decimals: int = 2, dur: int = 700):
        """Animate number counting up — dashboard revenue totals."""
        fmt = f"{{:.{decimals}f}}"
        def fn(t):
            v = from_v + (to_v - from_v) * t
            try:
                label.configure(text=f"{prefix}{fmt.format(v)}{suffix}")
            except Exception:
                pass
        self._add(fn, dur, ease=_ease_out)

    def pulse(self, widget, color_on: str, color_off: str,
              times: int = 2, dur: int = 200):
        """Flash widget for attention — notifications, alerts."""
        import tkinter as _tk
        def _do(n):
            if n <= 0:
                return
            try:
                widget.configure(bg=color_on)
            except Exception:
                return
            def _back(t):
                if t >= 1.0:
                    try:
                        widget.configure(bg=color_off)
                    except Exception:
                        pass
                    if self._root:
                        self._root.after(60, lambda: _do(n-1))
            self._add(_back, dur)
        _do(times)

    def shake(self, widget, amp: int = 8, dur: int = 320):
        """
        Shake widget left-right — error feedback.
        Widget must be placed with place() or in a canvas.
        For pack() widgets: temporarily stores and restores position.
        """
        try:
            x0 = widget.winfo_x()
            y0 = widget.winfo_y()
            p  = widget.winfo_parent()
        except Exception:
            return

        frame_n = [0]
        def fn(t):
            frame_n[0] += 1
            decay  = 1 - t
            offset = int(amp * decay * (1 if frame_n[0] % 2 == 0 else -1))
            try:
                widget.place_configure(x=x0 + offset, y=y0)
            except Exception:
                try:
                    widget.place(x=x0 + offset, y=y0)
                except Exception:
                    pass
        def restore():
            try:
                widget.place_forget()
                widget.pack()
            except Exception:
                pass
        self._add(fn, dur, ease=lambda t: t, done=restore)

    def smooth_drag(self, divider, panel,
                    min_w: int = 160, max_w: int = 600,
                    debounce: int = 2):
        """
        Smooth panel resize via drag divider.
        Replaces raw bind — debounced + visual feedback.

        Usage in staff.py:
            anim.smooth_drag(self._divider, self._stats_panel,
                             min_w=180, max_w=500)
        """
        counter = [0]
        last_w  = [0]

        def _drag(e):
            counter[0] += 1
            if counter[0] % debounce != 0:
                return
            try:
                sp_x  = panel.winfo_rootx()
                sp_w  = panel.winfo_width()
                new_w = max(min_w, min(max_w, sp_x + sp_w - e.x_root))
                if abs(new_w - last_w[0]) < 2:
                    return
                last_w[0] = new_w
                panel.configure(width=new_w)
            except Exception:
                pass

        def _enter(e):
            try:
                divider.configure(bg=C.get("teal", "#0ea5e9"))
            except Exception:
                pass

        def _leave(e):
            try:
                divider.configure(bg=C.get("sidebar", "#1e293b"))
            except Exception:
                pass

        divider.bind("<B1-Motion>", _drag)
        divider.bind("<Enter>",     _enter)
        divider.bind("<Leave>",     _leave)
        divider.configure(cursor="sb_h_double_arrow")


# Global singleton — import and use anywhere
anim = AnimationEngine()


