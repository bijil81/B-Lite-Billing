"""Style tokens for desktop-style context menus."""

MENU_STYLE = {
    "font_family": "Arial",
    "font_size": 10,
    "background": "#1f2937",
    "foreground": "#f8fafc",
    "active_background": "#2563eb",
    "active_foreground": "#ffffff",
    "disabled_foreground": "#64748b",
    "separator_color": "#334155",
    "danger_foreground": "#f87171",
    "padding_x": 8,
    "padding_y": 4,
}


def get_menu_style() -> dict[str, object]:
    return dict(MENU_STYLE)


def get_danger_style() -> dict[str, object]:
    style = get_menu_style()
    style["foreground"] = style["danger_foreground"]
    return style
