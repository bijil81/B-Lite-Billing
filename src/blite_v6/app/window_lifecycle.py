from __future__ import annotations


def hide_while_building(window) -> None:
    """Keep a Tk/Toplevel invisible while widgets are being constructed."""
    try:
        window.withdraw()
    except Exception:
        pass
    try:
        window.attributes("-alpha", 0.0)
    except Exception:
        pass


def reveal_when_ready(window) -> None:
    """Show a fully-built window without exposing a blank intermediate frame."""
    try:
        window.update_idletasks()
    except Exception:
        pass
    try:
        window.attributes("-alpha", 1.0)
    except Exception:
        pass
    try:
        window.deiconify()
    except Exception:
        pass
    try:
        window.lift()
    except Exception:
        pass
