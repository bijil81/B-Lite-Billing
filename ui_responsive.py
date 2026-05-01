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
    sz = max(8, font_sz + size_delta)
    if weight == "normal":
        return (family, sz)
    return (family, sz, weight)


def scaled_value(large: int, medium: int | None = None, compact: int | None = None):
    medium = medium if medium is not None else large
    compact = compact if compact is not None else medium
    current_mode = mode
    if current_mode == "large":
        return large
    if current_mode == "compact":
        return compact
    return medium


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


def _bind_mousewheel(canvas, widget):
    """Phase 3 FIX: cross-platform mousewheel binding."""
    def _on_mousewheel(event):
        try:
            if hasattr(event, "delta"):
                delta = event.delta
                if delta == 0:
                    return
                canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        except Exception:
            pass

    def _on_shift_mousewheel(event):
        try:
            if hasattr(event, "delta"):
                delta = event.delta
                if delta == 0:
                    return
                canvas.xview_scroll(int(-1 * (delta / 120)), "units")
        except Exception:
            pass

    for target in (canvas, widget):
        target.bind("<MouseWheel>", _on_mousewheel, add="+")
        target.bind("<Shift-MouseWheel>", _on_shift_mousewheel, add="+")


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
