"""
animation_engine.py — BOBY'S Salon UI Animation Engine
=======================================================
Add this class to ui_theme.py (bottom section).

Usage anywhere in app:
    from ui_theme import anim
    anim.color(widget, "#0ea5e9", "#0284c7", duration=150)
    anim.width(panel, 230, 380, duration=220)
    anim.slide_in(popup, direction="bottom")
    anim.pulse(btn)
    anim.shake(entry)
    anim.count_up(label, 0, 11165, prefix="₹", duration=800)
"""

import tkinter as tk
import time


# ── Easing functions ─────────────────────────────────────
def ease_out_cubic(t: float) -> float:
    """Decelerates — snappy start, soft landing."""
    return 1 - (1 - t) ** 3

def ease_in_out_cubic(t: float) -> float:
    """Smooth start and end."""
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2

def ease_out_back(t: float) -> float:
    """Slight overshoot — bouncy feel."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

def linear(t: float) -> float:
    return t


# ── Color helpers ─────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def _lerp_color(from_hex: str, to_hex: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(from_hex)
    r2, g2, b2 = _hex_to_rgb(to_hex)
    return _rgb_to_hex(
        r1 + (r2 - r1) * t,
        g1 + (g2 - g1) * t,
        b1 + (b2 - b1) * t,
    )


# ── Animation Engine ──────────────────────────────────────
class AnimationEngine:
    """
    Singleton animation controller.
    Uses root.after() for 60fps-ish tick loop.
    Access via global `anim` instance.
    """

    FPS      = 60
    TICK_MS  = int(1000 / FPS)   # ~16ms per frame

    def __init__(self):
        self._tasks: list[dict] = []   # active animations
        self._running = False
        self._root: tk.Tk | None = None

    def init(self, root: tk.Tk):
        """Call once after root window is created."""
        self._root = root
        if not self._running:
            self._running = True
            self._tick()

    # ── Tick loop ─────────────────────────────────────────
    def _tick(self):
        now     = time.perf_counter()
        active  = []
        for task in self._tasks:
            try:
                elapsed = now - task["start"]
                t_raw   = min(1.0, elapsed / task["duration"])
                t       = task["ease"](t_raw)
                task["step"](t)
                if t_raw < 1.0:
                    active.append(task)
                else:
                    task["step"](1.0)           # ensure final value
                    if task.get("on_complete"):
                        task["on_complete"]()
            except Exception:
                pass   # widget destroyed — silently drop
        self._tasks = active
        if self._root:
            self._root.after(self.TICK_MS, self._tick)

    def _add(self, step, duration_ms, ease=ease_out_cubic, on_complete=None):
        self._tasks.append({
            "start":       time.perf_counter(),
            "duration":    duration_ms / 1000,
            "step":        step,
            "ease":        ease,
            "on_complete": on_complete,
        })

    # ── Public API ────────────────────────────────────────

    def color(self, widget, from_hex: str, to_hex: str,
              prop: str = "bg", duration: int = 150):
        """
        Animate widget background or foreground color.
        prop: "bg" | "fg" | "activebackground"
        """
        def step(t):
            c = _lerp_color(from_hex, to_hex, t)
            try:
                widget.configure(**{prop: c})
            except Exception:
                pass
        self._add(step, duration, ease_out_cubic)

    def width(self, widget, from_w: int, to_w: int,
              duration: int = 220, ease=ease_out_cubic,
              on_complete=None):
        """Animate widget width (works best with pack_propagate(False))."""
        def step(t):
            w = int(from_w + (to_w - from_w) * t)
            try:
                widget.configure(width=w)
            except Exception:
                pass
        self._add(step, duration, ease, on_complete)

    def slide_in(self, widget, direction: str = "bottom",
                 offset: int = 30, duration: int = 250):
        """
        Slide widget into view from direction.
        Uses place() temporarily — widget must already be placed.
        direction: "bottom" | "top" | "left" | "right"
        """
        # Store original place config
        try:
            info   = widget.place_info()
            orig_y = int(info.get("y", 0))
            orig_x = int(info.get("x", 0))
        except Exception:
            return

        if direction == "bottom":
            start_y = orig_y + offset
            def step(t):
                y = int(start_y + (orig_y - start_y) * t)
                try:
                    widget.place_configure(y=y)
                except Exception:
                    pass
        elif direction == "top":
            start_y = orig_y - offset
            def step(t):
                y = int(start_y + (orig_y - start_y) * t)
                try:
                    widget.place_configure(y=y)
                except Exception:
                    pass
        elif direction == "right":
            start_x = orig_x + offset
            def step(t):
                x = int(start_x + (orig_x - start_x) * t)
                try:
                    widget.place_configure(x=x)
                except Exception:
                    pass
        else:
            return

        widget.place_configure(**({
            "bottom": {"y": start_y},
            "top":    {"y": start_y},
            "right":  {"x": start_x},
        }[direction]))
        self._add(step, duration, ease_out_cubic)

    def pulse(self, widget, color_on: str, color_off: str,
              times: int = 2, duration: int = 180):
        """Flash widget background N times — for attention/notification."""
        def _do_pulse(n):
            if n <= 0:
                return
            try:
                widget.configure(bg=color_on)
            except Exception:
                return

            def restore(t):
                if t >= 1.0:
                    try:
                        widget.configure(bg=color_off)
                    except Exception:
                        pass
                    if self._root:
                        self._root.after(80, lambda: _do_pulse(n - 1))
            self._add(restore, duration, linear)

        _do_pulse(times)

    def shake(self, widget, amplitude: int = 6, times: int = 4,
              duration: int = 300):
        """
        Shake widget left-right — for error feedback.
        Uses place() — widget must support it or be in a canvas.
        """
        try:
            info   = widget.place_info()
            orig_x = int(info.get("x", widget.winfo_x()))
        except Exception:
            orig_x = widget.winfo_x()

        total_frames = int(duration / self.TICK_MS)
        frame_count  = [0]

        def step(t):
            frame_count[0] += 1
            decay  = 1 - t   # diminishes over time
            offset = int(amplitude * decay *
                         (1 if frame_count[0] % 2 == 0 else -1))
            try:
                widget.place_configure(x=orig_x + offset)
            except Exception:
                pass
            if t >= 1.0:
                try:
                    widget.place_configure(x=orig_x)
                except Exception:
                    pass

        self._add(step, duration, linear)

    def count_up(self, label, from_val: float, to_val: float,
                 prefix: str = "₹", suffix: str = "",
                 decimals: int = 2, duration: int = 700,
                 ease=ease_out_cubic):
        """
        Animate a number counting up — dashboard revenue, totals.
        Example: anim.count_up(rev_label, 0, 11165.50, prefix="₹")
        """
        fmt = f"{{:.{decimals}f}}"
        def step(t):
            val = from_val + (to_val - from_val) * t
            try:
                label.configure(text=f"{prefix}{fmt.format(val)}{suffix}")
            except Exception:
                pass
        self._add(step, duration, ease)

    def smooth_drag(self, divider: tk.Widget, panel: tk.Widget,
                    min_w: int = 160, max_w: int = 600,
                    debounce: int = 2):
        """
        Attach smooth drag resize to a divider widget.
        debounce: update every N drag events (reduces jitter).

        Usage:
            anim.smooth_drag(self._divider, self._stats_panel,
                             min_w=180, max_w=500)
        """
        counter = [0]
        last_w  = [panel.winfo_width() or 230]

        def on_drag(e):
            counter[0] += 1
            if counter[0] % debounce != 0:
                return   # skip frames → smoother

            sp_x   = panel.winfo_rootx()
            sp_w   = panel.winfo_width()
            new_w  = max(min_w, min(max_w,
                         sp_x + sp_w - e.x_root))

            if abs(new_w - last_w[0]) < 2:
                return   # sub-pixel change — skip

            last_w[0] = new_w
            try:
                panel.configure(width=new_w)
            except Exception:
                pass

        def on_enter(e):
            try:
                divider.configure(bg="#0ea5e9")   # teal highlight
            except Exception:
                pass

        def on_leave(e):
            try:
                divider.configure(bg="#1e293b")   # sidebar color
            except Exception:
                pass

        divider.bind("<B1-Motion>", on_drag)
        divider.bind("<Enter>",     on_enter)
        divider.bind("<Leave>",     on_leave)

    def page_transition(self, old_frame: tk.Widget,
                         new_frame: tk.Widget, duration: int = 180):
        """
        Fade page switch — color interpolation on content frame.
        Simple: bg dims then brightens as new content appears.
        """
        from utils import C
        bg = C.get("bg", "#0f172a")

        def dim(t):
            try:
                old_frame.configure(bg=_lerp_color(bg, "#000000", t * 0.3))
            except Exception:
                pass
            if t >= 1.0:
                try:
                    old_frame.pack_forget()
                    new_frame.pack(fill=tk.BOTH, expand=True)
                except Exception:
                    pass

        self._add(dim, duration // 2, ease_out_cubic,
                  on_complete=lambda: None)


# ── Global singleton ─────────────────────────────────────
anim = AnimationEngine()
