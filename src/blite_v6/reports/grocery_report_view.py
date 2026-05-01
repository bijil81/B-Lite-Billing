"""Grocery report UI panel with day/week/month filters."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from date_helpers import attach_date_mask, display_to_iso_date, iso_to_display_date, today_display_str, validate_display_date
from ui_theme import ModernButton
from utils import C, fmt_currency

from .retail_summary import (
    build_closing_retail_summary,
    build_gst_summary,
    build_product_sales_summary,
    format_quantity,
)


ReportReader = Callable[[str, str, str], list[dict[str, Any]]]


def _configure_tree_columns(tree: ttk.Treeview, specs: list[tuple[str, str, int, str, bool]]) -> None:
    for col, heading, width, anchor, stretch in specs:
        tree.heading(col, text=heading, anchor=anchor)
        tree.column(
            col,
            width=width,
            minwidth=min(width, 80),
            anchor=anchor,
            stretch=stretch,
        )


@dataclass(frozen=True)
class PeriodRange:
    label: str
    from_date: str
    to_date: str


def resolve_period_range(period: str, today: date | None = None) -> PeriodRange:
    today = today or date.today()
    key = str(period or "month").strip().lower()
    if key == "day":
        start = today
        label = "Today"
    elif key == "week":
        start = today - timedelta(days=today.weekday())
        label = "This Week"
    elif key == "month":
        start = today.replace(day=1)
        label = "This Month"
    else:
        start = today.replace(day=1)
        label = "Custom"
    return PeriodRange(label, start.isoformat(), today.isoformat())


class GroceryReportPanel(tk.Frame):
    def __init__(self, parent, *, read_rows: ReportReader):
        super().__init__(parent, bg=C["bg"])
        self._read_rows = read_rows
        self._period = "month"
        self._build()

    def _build(self) -> None:
        controls = tk.Frame(self, bg=C["card"], padx=14, pady=9)
        controls.pack(fill=tk.X, padx=10, pady=(2, 8))

        tk.Label(
            controls,
            text="Grocery Summary",
            bg=C["card"],
            fg=C["text"],
            font=("Arial", 11, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 14))

        for text, period, color in [
            ("Today", "day", C["blue"]),
            ("This Week", "week", C["teal"]),
            ("This Month", "month", C["purple"]),
        ]:
            ModernButton(
                controls,
                text=text,
                command=lambda p=period: self.set_period(p),
                color=color,
                hover_color=C["blue"],
                width=98,
                height=30,
                radius=8,
                font=("Arial", 10, "bold"),
            ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(controls, text="From:", bg=C["card"], fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT, padx=(8, 4))
        self.from_ent = tk.Entry(controls, font=("Arial", 10), bg=C["input"], fg=C["text"], bd=0, width=13, insertbackground=C["accent"])
        self.from_ent.pack(side=tk.LEFT, ipady=5, padx=(0, 8))
        attach_date_mask(self.from_ent)

        tk.Label(controls, text="To:", bg=C["card"], fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 4))
        self.to_ent = tk.Entry(controls, font=("Arial", 10), bg=C["input"], fg=C["text"], bd=0, width=13, insertbackground=C["accent"])
        self.to_ent.pack(side=tk.LEFT, ipady=5, padx=(0, 8))
        attach_date_mask(self.to_ent)

        ModernButton(
            controls,
            text="Apply",
            command=self.refresh,
            color=C["green"],
            hover_color="#1a7a45",
            width=82,
            height=30,
            radius=8,
            font=("Arial", 10, "bold"),
        ).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(controls, text="", bg=C["card"], fg=C["muted"], font=("Arial", 10))
        self.status_lbl.pack(side=tk.RIGHT, padx=(8, 0))

        self.cards = tk.Frame(self, bg=C["bg"])
        self.cards.pack(fill=tk.X, padx=10, pady=(0, 8))

        pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=6, bg=C["bg"])
        pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        product_wrap = tk.Frame(pane, bg=C["bg"])
        pane.add(product_wrap, minsize=620)
        tk.Label(product_wrap, text="Product Sales", bg=C["bg"], fg=C["accent"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 4))
        product_cols = ("Product", "QtyUnit", "Revenue", "Cost", "Margin")
        self.product_tree = ttk.Treeview(product_wrap, columns=product_cols, show="headings", height=18)
        _configure_tree_columns(
            self.product_tree,
            [
                ("Product", "Product", 320, tk.W, True),
                ("QtyUnit", "Qty / Unit", 110, tk.E, False),
                ("Revenue", "Revenue", 130, tk.E, False),
                ("Cost", "Cost Rs", 110, tk.E, False),
                ("Margin", "Margin Rs", 110, tk.E, False),
            ],
        )
        p_scroll = ttk.Scrollbar(product_wrap, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=p_scroll.set)
        self.product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        p_scroll.pack(side=tk.LEFT, fill=tk.Y)

        tax_wrap = tk.Frame(pane, bg=C["bg"])
        pane.add(tax_wrap, minsize=360)
        tk.Label(tax_wrap, text="GST Summary", bg=C["bg"], fg=C["accent"], font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 4))
        gst_cols = ("GST Rate", "Taxable", "GST", "Gross")
        self.gst_tree = ttk.Treeview(tax_wrap, columns=gst_cols, show="headings", height=18)
        _configure_tree_columns(
            self.gst_tree,
            [
                ("GST Rate", "GST Rate", 100, tk.W, False),
                ("Taxable", "Taxable", 130, tk.E, False),
                ("GST", "GST", 110, tk.E, False),
                ("Gross", "Gross", 130, tk.E, False),
            ],
        )
        g_scroll = ttk.Scrollbar(tax_wrap, orient="vertical", command=self.gst_tree.yview)
        self.gst_tree.configure(yscrollcommand=g_scroll.set)
        self.gst_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        g_scroll.pack(side=tk.LEFT, fill=tk.Y)

        self.set_period("month")

    def set_period(self, period: str) -> None:
        self._period = period
        resolved = resolve_period_range(period)
        self.from_ent.delete(0, tk.END)
        self.from_ent.insert(0, iso_to_display_date(resolved.from_date))
        self.to_ent.delete(0, tk.END)
        self.to_ent.insert(0, today_display_str() if resolved.to_date == date.today().isoformat() else iso_to_display_date(resolved.to_date))
        self.refresh()

    def _selected_range(self) -> tuple[str, str]:
        from_text = self.from_ent.get().strip()
        to_text = self.to_ent.get().strip()
        from_iso = display_to_iso_date(from_text) if validate_display_date(from_text) else from_text
        to_iso = display_to_iso_date(to_text) if validate_display_date(to_text) else to_text
        return from_iso, to_iso

    def refresh(self) -> None:
        from_iso, to_iso = self._selected_range()
        rows = self._read_rows(from_iso, to_iso, "")
        product_rows = build_product_sales_summary(rows)
        gst_rows = build_gst_summary(rows)
        summary = build_closing_retail_summary(rows, ())

        self._render_cards(summary)
        self._render_products(product_rows)
        self._render_gst(gst_rows)
        self.status_lbl.config(text=f"{len(rows)} bill(s) | {from_iso} to {to_iso}")

    def _render_cards(self, summary) -> None:
        for child in self.cards.winfo_children():
            child.destroy()
        card_specs = [
            ("Gross Sales", summary.gross_sales, C["blue"]),
            ("Net Revenue", summary.revenue, C["teal"]),
            ("Product Sales", summary.product_revenue, C["purple"]),
            ("Discount", summary.discount, C["orange"]),
            ("GST", summary.gst_total, C["green"]),
            ("Bills", summary.bill_count, "#636e72"),
        ]
        for label, value, color in card_specs:
            card = tk.Frame(self.cards, bg=color, padx=16, pady=8)
            card.pack(side=tk.LEFT, padx=(0, 6), fill=tk.X, expand=True)
            display = str(value) if label == "Bills" else fmt_currency(value)
            tk.Label(card, text=display, font=("Arial", 12, "bold"), bg=color, fg="white").pack(anchor="w")
            tk.Label(card, text=label, font=("Arial", 9), bg=color, fg="white").pack(anchor="w")

    def _render_products(self, rows) -> None:
        for iid in self.product_tree.get_children():
            self.product_tree.delete(iid)
        for row in rows:
            self.product_tree.insert(
                "",
                tk.END,
                values=(
                    row.name,
                    f"{format_quantity(row.quantity)} {row.unit}".strip(),
                    fmt_currency(row.revenue),
                    fmt_currency(row.cost),
                    fmt_currency(row.profit),
                ),
            )

    def _render_gst(self, rows) -> None:
        for iid in self.gst_tree.get_children():
            self.gst_tree.delete(iid)
        if not rows:
            self.gst_tree.insert(
                "",
                tk.END,
                values=("No GST collected", fmt_currency(0), fmt_currency(0), fmt_currency(0)),
            )
            return
        for row in rows:
            rate_text = "Unspecified" if row.rate < 0 else f"{format_quantity(row.rate)}%"
            self.gst_tree.insert(
                "",
                tk.END,
                values=(
                    rate_text,
                    fmt_currency(row.taxable_amount),
                    fmt_currency(row.gst_amount),
                    fmt_currency(row.gross_amount),
                ),
            )
