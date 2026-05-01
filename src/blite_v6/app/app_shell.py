from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ShellMetrics:
    ui_scale: float
    responsive: dict
    compact: bool
    sidebar_width: int
    nav_font_size: int
    nav_padx: int
    nav_pady: int
    sidebar_button_height: int
    user_button_width: int


def _safe_float(value: object, default: float = 1.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_shell_metrics(
    settings: Mapping[str, object] | None,
    responsive_metrics: Mapping[str, object] | None,
) -> ShellMetrics:
    settings = settings or {}
    responsive_source = responsive_metrics or {}
    responsive = {
        "mode": responsive_source.get("mode", "medium"),
        "sidebar_w": int(responsive_source.get("sidebar_w", 190) or 190),
        "padding": int(responsive_source.get("padding", 8) or 8),
        "font_sz": int(responsive_source.get("font_sz", 10) or 10),
        "btn_h": int(responsive_source.get("btn_h", 32) or 32),
    }
    ui_scale = _safe_float(settings.get("ui_scale", 1.0), 1.0)
    compact = responsive["mode"] == "compact"
    sidebar_width = max(150, int(responsive["sidebar_w"] * ui_scale))
    nav_font_size = max(9, int((responsive["font_sz"] + 1) * ui_scale))
    nav_padx = max(8, int((responsive["padding"] + 6) * ui_scale))
    nav_pady = max(4, int((responsive["padding"] + (0 if compact else 2)) * ui_scale))
    sidebar_button_height = max(28, int((responsive["btn_h"] + (-2 if compact else 0)) * ui_scale))
    user_button_width = max(124, sidebar_width - 24)
    return ShellMetrics(
        ui_scale=ui_scale,
        responsive=responsive,
        compact=compact,
        sidebar_width=sidebar_width,
        nav_font_size=nav_font_size,
        nav_padx=nav_padx,
        nav_pady=nav_pady,
        sidebar_button_height=sidebar_button_height,
        user_button_width=user_button_width,
    )


def sidebar_drag_bounds(responsive: Mapping[str, object]) -> tuple[int, int]:
    sidebar_width = int(responsive.get("sidebar_w", 190) or 190)
    return max(140, sidebar_width - 30), max(260, sidebar_width + 80)
