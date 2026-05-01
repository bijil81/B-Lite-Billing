from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from src.blite_v6.billing.cart_operations import display_quantity_unit, unit_type_for_variant
from src.blite_v6.billing.split_layout import billing_left_width


def resolve_billing_mode(settings: dict[str, Any]) -> dict[str, Any]:
    billing_mode = settings.get("billing_mode", "mixed")
    show_services = billing_mode in ("mixed", "service_only")
    show_products = billing_mode in ("mixed", "product_only")
    return {
        "billing_mode": billing_mode,
        "show_services": show_services,
        "show_products": show_products,
        "initial_mode": "services" if show_services else "products",
    }


def quantity_unit_hint_view(
    *,
    current_mode: str,
    selected_variant: dict[str, Any] | None,
) -> dict[str, Any]:
    visible = current_mode == "products"
    if not visible:
        return {
            "visible": False,
            "qty_label": "Qty:",
            "unit_badge": "",
            "helper": "",
            "show_helper": False,
        }

    if not selected_variant:
        return {
            "visible": True,
            "qty_label": "Qty:",
            "unit_badge": "Unit: select item",
            "helper": "",
            "show_helper": False,
        }

    unit = unit_type_for_variant(selected_variant)
    display_unit = display_quantity_unit(unit)
    helper_by_unit = {
        "kg": "Enter 1.24 or 1240g",
        "g": "Enter grams, e.g. 250",
        "L": "Enter 0.5 or 500ml",
        "ml": "Enter ml, e.g. 500",
        "pcs": "Pieces / packets",
    }
    return {
        "visible": True,
        "qty_label": f"Qty ({display_unit}):" if display_unit != "pcs" else "Qty (pcs):",
        "unit_badge": f"Unit: {display_unit}",
        "helper": helper_by_unit.get(display_unit, f"Enter quantity in {display_unit}"),
        "show_helper": display_unit != "pcs",
    }


def calculate_bill_preview_font(screen_height: int) -> int:
    return max(9, min(14, int(screen_height / 80)))


def calculate_left_panel_width(
    screen_width: int,
    ui_scale: float,
    compact_mode: bool,
    min_width: int,
    max_width: int,
) -> int:
    width_ratio = 0.36 if compact_mode else 0.32
    return max(min_width, min(max_width, int(screen_width * width_ratio * ui_scale)))


def finish_action_specs(widths: dict[str, int]) -> tuple[dict[str, Any], ...]:
    return (
        {"group": "secondary", "text": "PRINT", "color": "#0984e3", "hover": "#0652a0", "command": "print_bill", "width": widths["print"]},
        {"group": "secondary", "text": "PDF", "color": "#6c5ce7", "hover": "#4834d4", "command": "save_pdf", "width": widths["pdf"]},
        {"group": "primary", "text": "SAVE", "color_key": "purple", "hover": "#6c3483", "command": "manual_save", "width": widths["save"]},
        {"group": "primary", "text": "WA", "color": "#25d366", "hover": "#1a9e4a", "command": "send_whatsapp", "width": widths["wa"]},
        {"group": "primary", "text": "CLEAR", "color_key": "red", "hover": "#c0392b", "command": "clear_all", "width": widths["clear"]},
    )


def configure_billing_combobox_style(colors: dict[str, str]) -> None:
    style = ttk.Style()
    style.configure(
        "Billing.TCombobox",
        fieldbackground=colors["input"],
        background=colors["input"],
        foreground=colors["text"],
        selectbackground=colors["teal"],
        selectforeground="white",
        arrowcolor=colors["accent"],
        borderwidth=0,
    )
    style.map(
        "Billing.TCombobox",
        fieldbackground=[("readonly", colors["input"]), ("disabled", colors["sidebar"])],
        foreground=[("readonly", colors["text"]), ("disabled", colors["muted"])],
        selectbackground=[("readonly", colors["teal"])],
        selectforeground=[("readonly", "white")],
    )


def create_scrollable_panel(parent, width: int, colors: dict[str, str]) -> dict[str, Any]:
    outer = tk.Frame(parent, bg=colors["bg"], width=width)
    outer.pack_propagate(False)

    canvas = tk.Canvas(outer, bg=colors["bg"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    body = tk.Frame(canvas, bg=colors["bg"])
    window_id = canvas.create_window((0, 0), window=body, anchor="nw")

    body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfig(window_id, width=event.width))

    def _scroll(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", _scroll))
    canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

    return {"outer": outer, "canvas": canvas, "scrollbar": scrollbar, "body": body}


def create_intro_card(
    parent,
    colors: dict[str, str],
    title_font: tuple[Any, ...],
    meta_font: tuple[Any, ...],
    padx: int,
    pady: int,
) -> tk.Frame:
    intro = tk.Frame(parent, bg=colors["card"], padx=padx, pady=pady)
    intro.pack(fill=tk.X, pady=(0, 8))
    tk.Label(intro, text="Billing Workspace", font=title_font, bg=colors["card"], fg=colors["text"]).pack(anchor="w")
    tk.Label(
        intro,
        text="Build the bill on the left, review and deliver from the right.",
        font=meta_font,
        bg=colors["card"],
        fg=colors["muted"],
    ).pack(anchor="w", pady=(3, 0))
    return intro


def create_card_section(
    parent,
    colors: dict[str, str],
    title: str,
    subtitle: str,
    accent_color: str,
    title_font: tuple[Any, ...],
    subtitle_font: tuple[Any, ...],
    outer_pady: int | tuple[int, int] = 4,
    header_padx: int = 12,
    header_pady: int = 6,
    body_padx: int = 12,
    body_pady: int = 8,
    title_fg: str | None = None,
) -> tk.Frame:
    outer = tk.Frame(parent, bg=colors["card"])
    outer.pack(fill=tk.X, pady=outer_pady)
    header = tk.Frame(outer, bg=colors["sidebar"], padx=header_padx, pady=header_pady)
    header.pack(fill=tk.X)
    title_label = tk.Label(
        header,
        text=title,
        font=title_font,
        bg=colors["sidebar"],
        fg=title_fg or colors["text"],
    )
    title_label.pack(side=tk.LEFT)
    tk.Label(
        header,
        text=subtitle,
        font=subtitle_font,
        bg=colors["sidebar"],
        fg=colors["muted"],
    ).pack(side=tk.RIGHT)
    tk.Frame(outer, bg=accent_color, height=2).pack(fill=tk.X)
    body = tk.Frame(outer, bg=colors["card"], padx=body_padx, pady=body_pady)
    body.pack(fill=tk.X)
    body.section_title_label = title_label
    return body


def resize_preview_font(panel, text_widget, event=None) -> None:
    try:
        width = panel.winfo_width()
        if width < 100:
            return
        event_width = getattr(event, "width", width) if event else width
        if event_width < 100:
            return
        new_font_size = max(8, min(14, int(event_width / 65)))
        current_font = text_widget.cget("font")
        if str(new_font_size) not in str(current_font):
            text_widget.configure(font=("Courier New", new_font_size))
    except Exception:
        pass


def sync_billing_split(
    paned,
    left_panel,
    host,
    get_metrics: Callable[[Any], dict[str, Any]],
    scaled: Callable[[int, int, int], int],
) -> None:
    try:
        total_width = paned.winfo_width()
        if total_width < 300:
            return
        min_left = scaled(620, 520, 420)
        min_preview = scaled(340, 300, 240)
        left_width = billing_left_width(total_width, min_left, min_preview)
        paned.sashpos(0, left_width)
        left_panel.configure(width=left_width)
    except Exception:
        pass
