import tkinter as tk
from tkinter import ttk


_RESPONSIVE_DEFAULTS = {
    "mode": "medium",
    "sidebar_w": 190,
    "preview_ratio": 0.38,
    "btn_h": 32,
    "font_sz": 10,
    "row_h": 30,
    "padding": 8,
}

mode = _RESPONSIVE_DEFAULTS["mode"]
sidebar_w = _RESPONSIVE_DEFAULTS["sidebar_w"]
preview_ratio = _RESPONSIVE_DEFAULTS["preview_ratio"]
btn_h = _RESPONSIVE_DEFAULTS["btn_h"]
font_sz = _RESPONSIVE_DEFAULTS["font_sz"]
row_h = _RESPONSIVE_DEFAULTS["row_h"]
padding = _RESPONSIVE_DEFAULTS["padding"]
manual_ui_scale = 1.0


def _normalize_manual_scale(value) -> float:
    try:
        scale = float(value)
    except Exception:
        scale = 1.0
    return max(0.85, min(1.25, scale))


def set_manual_ui_scale(value) -> float:
    global manual_ui_scale
    manual_ui_scale = _normalize_manual_scale(value)
    return manual_ui_scale


def get_manual_ui_scale() -> float:
    return manual_ui_scale


def _load_manual_ui_scale() -> float:
    try:
        from salon_settings import get_settings
        return set_manual_ui_scale(get_settings().get("ui_scale", 1.0))
    except Exception:
        return manual_ui_scale


def _apply_manual_scale(value: int | float) -> int:
    return max(1, int(round(float(value) * manual_ui_scale)))


def compute_responsive_metrics(sw: int, sh: int):
    """Compute layout metrics based on screen dimensions.

    Phase 3 FIX: Added DPI-aware breakpoints for 125%, 150%, 175%, 200% scaling.
    Also handles ultrawide, 1366x768, and multi-monitor correctly.
    """
    if sw >= 1440 and sh >= 900:
        return {
            "mode": "large",
            "sidebar_w": 220,
            "preview_ratio": 0.42,
            "btn_h": 36,
            "font_sz": 11,
            "row_h": 34,
            "padding": 10,
        }
    if sw >= 1280 and sh >= 760:
        return {
            "mode": "medium",
            "sidebar_w": 190,
            "preview_ratio": 0.38,
            "btn_h": 32,
            "font_sz": 10,
            "row_h": 30,
            "padding": 8,
        }
    return {
        "mode": "compact",
        "sidebar_w": 160,
        "preview_ratio": 0.32,
        "btn_h": 28,
        "font_sz": 9,
        "row_h": 26,
        "padding": 6,
    }


def get_current_font_size():
    """Return the active font size. Call this for dynamic font scaling."""
    return font_sz


def get_current_spacing():
    """Return the active padding value. Call this for dynamic spacing."""
    return padding


def initialize_responsive(root):
    global mode, sidebar_w, preview_ratio, btn_h, font_sz, row_h, padding
    try:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
    except Exception:
        sw, sh = 1366, 768
    _load_manual_ui_scale()
    metrics = compute_responsive_metrics(sw, sh)
    mode = metrics["mode"]
    sidebar_w = metrics["sidebar_w"]
    preview_ratio = metrics["preview_ratio"]
    btn_h = metrics["btn_h"]
    font_sz = metrics["font_sz"]
    row_h = metrics["row_h"]
    padding = metrics["padding"]
    return metrics


def get_responsive_metrics(root=None):
    if root is None:
        return {
            "mode": mode,
            "sidebar_w": sidebar_w,
            "preview_ratio": preview_ratio,
            "btn_h": btn_h,
            "font_sz": font_sz,
            "row_h": row_h,
            "padding": padding,
        }
    try:
        root.update_idletasks()
        return compute_responsive_metrics(
            root.winfo_screenwidth(),
            root.winfo_screenheight(),
        )
    except Exception:
        return {
            "mode": mode,
            "sidebar_w": sidebar_w,
            "preview_ratio": preview_ratio,
            "btn_h": btn_h,
            "font_sz": font_sz,
            "row_h": row_h,
            "padding": padding,
        }


def font(size_delta: int = 0, weight: str = "normal", family: str = "Arial"):
    sz = max(8, _apply_manual_scale(font_sz + size_delta))
    if weight == "normal":
        return (family, sz)
    return (family, sz, weight)


def scaled_value(large: int, medium: int | None = None, compact: int | None = None):
    medium = medium if medium is not None else large
    compact = compact if compact is not None else medium
    current_mode = mode
    if current_mode == "large":
        return _apply_manual_scale(large)
    if current_mode == "compact":
        return _apply_manual_scale(compact)
    return _apply_manual_scale(medium)


def scale_for_dpi(base_value: int, root=None) -> int:
    """Phase 3 FIX: Scale a pixel value for the current DPI setting.

    Returns base_value multiplied by the DPI scale factor from
    tk.scaling or falls back to system DPI via winfo_fpixels.
    """
    try:
        if root is None:
            root = tk._default_root
        if root is not None:
            fps = root.winfo_fpixels("1i")
            if fps > 96:  # DPI > 100%
                scale = fps / 96.0
                return int(base_value * scale)
    except Exception:
        pass
    return base_value


def fit_toplevel(win, width: int, height: int, *,
                 min_width: int = 420,
                 min_height: int = 320,
                 resizable: bool = True,
                 anchor: str = "center",
                 margin: int = 20,
                 top_offset: int = 30,
                 right_offset: int = 20):
    """
    Fit a Toplevel within the current screen while keeping it resizable.
    anchor:
      - "center"
      - "topright"
    """
    try:
        owner = win.master.winfo_toplevel() if getattr(win, "master", None) else None
        if owner and owner != win:
            win.transient(owner)
    except Exception:
        pass

    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()

    max_w = max(320, sw - (margin * 2))
    max_h = max(260, sh - max(top_offset, margin) - margin)

    width = min(width, max_w)
    height = min(height, max_h)

    if anchor == "topright":
        x = max(margin, sw - width - right_offset)
        y = max(20, top_offset)
    else:
        x = max(margin, (sw - width) // 2)
        y = max(20, (sh - height) // 2)

    win.geometry(f"{width}x{height}+{x}+{y}")
    win.minsize(min(width, min_width), min(height, min_height))
    win.resizable(resizable, resizable)
    return width, height


_ACTIVE_SCROLL_CANVAS = None
_MOUSEWHEEL_GLOBAL_BOUND = False
_SCROLL_CANVASES = []


def _wheel_scroll_units(delta) -> int:
    """Normalize classic mouse wheels and precision touchpads to Tk scroll units."""
    try:
        delta = float(delta)
    except Exception:
        return 0
    if delta == 0:
        return 0
    magnitude = max(1, int(abs(delta) / 120))
    return -magnitude if delta > 0 else magnitude


def _is_dropdown_wheel_target(widget) -> bool:
    """Return True when wheel belongs to a dropdown/list control, not the page."""
    try:
        cls = str(widget.winfo_class())
    except Exception:
        cls = ""
    try:
        path = str(widget)
    except Exception:
        path = ""
    if cls in {"TCombobox", "Combobox"}:
        return True
    if "combobox" in path.lower() and "popdown" in path.lower():
        return True
    return cls == "Listbox" and "popdown" in path.lower()


def _bind_mousewheel(canvas, widget):
    """Cross-platform mousewheel binding that also works over child inputs."""
    global _MOUSEWHEEL_GLOBAL_BOUND
    if canvas not in _SCROLL_CANVASES:
        _SCROLL_CANVASES.append(canvas)

    def _activate(_event=None):
        global _ACTIVE_SCROLL_CANVAS
        _ACTIVE_SCROLL_CANVAS = canvas

    def _deactivate(_event=None):
        global _ACTIVE_SCROLL_CANVAS
        if _ACTIVE_SCROLL_CANVAS is canvas:
            _ACTIVE_SCROLL_CANVAS = None

    def _target_canvas(event=None, fallback=False):
        try:
            x = event.x_root if event is not None else None
            y = event.y_root if event is not None else None
            if x is not None and y is not None:
                for candidate in reversed(_SCROLL_CANVASES):
                    if not candidate.winfo_exists():
                        continue
                    cx = candidate.winfo_rootx()
                    cy = candidate.winfo_rooty()
                    cw = candidate.winfo_width()
                    ch = candidate.winfo_height()
                    if cx <= x <= cx + cw and cy <= y <= cy + ch:
                        return candidate
        except Exception:
            pass
        return _ACTIVE_SCROLL_CANVAS or (canvas if fallback else None)

    def _on_mousewheel(event):
        try:
            if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                return "break"
            target = _target_canvas(event, fallback=True)
            if target is None:
                return None
            if hasattr(event, "delta"):
                units = _wheel_scroll_units(event.delta)
                if units == 0:
                    return None
                target.yview_scroll(units, "units")
                return "break"
        except Exception:
            pass
        return None

    def _on_shift_mousewheel(event):
        try:
            if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                return "break"
            target = _target_canvas(event, fallback=True)
            if target is None:
                return None
            if hasattr(event, "delta"):
                units = _wheel_scroll_units(event.delta)
                if units == 0:
                    return None
                target.xview_scroll(units, "units")
                return "break"
        except Exception:
            pass
        return None

    def _on_button4(event):
        try:
            if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                return "break"
            target = _target_canvas(event, fallback=True)
            if target is not None:
                target.yview_scroll(-1, "units")
                return "break"
        except Exception:
            pass
        return None

    def _on_button5(event):
        try:
            if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                return "break"
            target = _target_canvas(event, fallback=True)
            if target is not None:
                target.yview_scroll(1, "units")
                return "break"
        except Exception:
            pass
        return None

    def _bind_tree(target):
        try:
            if not getattr(target, "_blite_scroll_bound", False):
                target._blite_scroll_bound = True
                target.bind("<Enter>", _activate, add="+")
                target.bind("<Leave>", _deactivate, add="+")
                target.bind("<MouseWheel>", _on_mousewheel, add="+")
                target.bind("<Shift-MouseWheel>", _on_shift_mousewheel, add="+")
                target.bind("<Button-4>", _on_button4, add="+")
                target.bind("<Button-5>", _on_button5, add="+")
                target.bind("<Configure>", lambda _e: _bind_tree(target), add="+")
        except Exception:
            pass
        try:
            for child in target.winfo_children():
                _bind_tree(child)
        except Exception:
            pass

    for target in (canvas, widget):
        _bind_tree(target)

    if not _MOUSEWHEEL_GLOBAL_BOUND:
        root = canvas.winfo_toplevel()

        def _on_global_mousewheel(event):
            try:
                if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                    return "break"
                active = _target_canvas(event)
                if active is None:
                    return
                if hasattr(event, "delta"):
                    units = _wheel_scroll_units(event.delta)
                    if units == 0:
                        return
                    active.yview_scroll(units, "units")
                    return "break"
            except Exception:
                pass

        def _on_global_shift_mousewheel(event):
            try:
                if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                    return "break"
                active = _target_canvas(event)
                if active is None:
                    return
                if hasattr(event, "delta"):
                    units = _wheel_scroll_units(event.delta)
                    if units == 0:
                        return
                    active.xview_scroll(units, "units")
                    return "break"
            except Exception:
                pass

        def _on_global_button4(event):
            try:
                if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                    return "break"
                active = _target_canvas(event)
                if active is not None:
                    active.yview_scroll(-1, "units")
                    return "break"
            except Exception:
                pass

        def _on_global_button5(event):
            try:
                if _is_dropdown_wheel_target(getattr(event, "widget", None)):
                    return "break"
                active = _target_canvas(event)
                if active is not None:
                    active.yview_scroll(1, "units")
                    return "break"
            except Exception:
                pass

        root.bind_all("<MouseWheel>", _on_global_mousewheel, add="+")
        root.bind_all("<Shift-MouseWheel>", _on_global_shift_mousewheel, add="+")
        root.bind_all("<Button-4>", _on_global_button4, add="+")
        root.bind_all("<Button-5>", _on_global_button5, add="+")
        _MOUSEWHEEL_GLOBAL_BOUND = True


def make_scrollable(parent, *, bg: str = None, padx: int = 0, pady: int = 0,
                    horizontal: bool = False):
    """
    Reusable Canvas + Frame scroll wrapper.
    Returns: (body, canvas, container)
    """
    container = tk.Frame(parent, bg=bg or parent.cget("bg"))
    container.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(container, bg=bg or parent.cget("bg"),
                       highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    hsb = None
    if horizontal:
        hsb = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

    body = tk.Frame(canvas, bg=bg or parent.cget("bg"), padx=padx, pady=pady)
    cwin = canvas.create_window((0, 0), window=body, anchor="nw")

    def _sync_scrollregion(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_width(event):
        item_kwargs = {}
        if horizontal:
            item_kwargs["height"] = max(body.winfo_reqheight(), event.height)
        else:
            item_kwargs["width"] = event.width
        canvas.itemconfigure(cwin, **item_kwargs)

    body.bind("<Configure>", _sync_scrollregion)
    canvas.bind("<Configure>", _sync_width)
    _bind_mousewheel(canvas, body)
    return body, canvas, container


def make_toplevel_scrollable(win, *, bg: str = None, padx: int = 0, pady: int = 0,
                             horizontal: bool = False):
    """Scrollable body helper for large Toplevel forms."""
    win.grid_rowconfigure(0, weight=1)
    win.grid_columnconfigure(0, weight=1)
    return make_scrollable(win, bg=bg, padx=padx, pady=pady, horizontal=horizontal)


def make_toplevel_scrollable_with_footer(win, *, bg: str = None, padx: int = 0, pady: int = 0,
                                         footer_bg: str = None, footer_padx: int = 14,
                                         footer_pady: int = 10, horizontal: bool = False):
    """
    Toplevel layout for production forms:
    - scrollable content body
    - fixed bottom action bar that remains visible while the body scrolls

    Returns: (body, footer, canvas, container)
    """
    bg = bg or win.cget("bg")
    footer_bg = footer_bg or bg
    footer = tk.Frame(win, bg=footer_bg, padx=footer_padx, pady=footer_pady)
    footer.pack(side=tk.BOTTOM, fill=tk.X)
    body, canvas, container = make_scrollable(
        win, bg=bg, padx=padx, pady=pady, horizontal=horizontal
    )
    return body, footer, canvas, container
