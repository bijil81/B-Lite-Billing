from __future__ import annotations


def dpi_snapshot(root) -> dict[str, float | int]:
    """Capture runtime scale metrics that can change with Windows display scaling."""
    try:
        root.update_idletasks()
    except Exception:
        pass
    try:
        dpi = float(root.winfo_fpixels("1i"))
    except Exception:
        dpi = 96.0
    try:
        screen_w = int(root.winfo_screenwidth())
        screen_h = int(root.winfo_screenheight())
    except Exception:
        screen_w, screen_h = 1366, 768
    try:
        tk_scaling = float(root.tk.call("tk", "scaling"))
    except Exception:
        tk_scaling = dpi / 72.0
    return {
        "dpi": round(dpi, 2),
        "screen_w": screen_w,
        "screen_h": screen_h,
        "tk_scaling": round(tk_scaling, 4),
    }


def dpi_snapshot_changed(previous: dict | None, current: dict) -> bool:
    if not previous:
        return True
    return (
        abs(float(previous.get("dpi", 0)) - float(current.get("dpi", 0))) >= 1
        or previous.get("screen_w") != current.get("screen_w")
        or previous.get("screen_h") != current.get("screen_h")
    )


def tk_scaling_for_dpi(dpi: float | int) -> float:
    try:
        dpi = float(dpi)
    except Exception:
        dpi = 96.0
    return max(1.0, dpi / 72.0)
