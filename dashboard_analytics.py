import tkinter as tk
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import gc

from services_v5.analytics_service import (
    get_daily_revenue_trend,
    get_top_selling_items,
    get_payment_methods_breakdown
)
from utils import C

# Use aggressive non-interactive backend to avoid memory leaks
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _safe_destroy_canvas(canvas):
    """Safely destroy matplotlib canvas and aggressively free memory."""
    if canvas:
        try:
            canvas.get_tk_widget().destroy()
            if hasattr(canvas, "figure"):
                canvas.figure.clf()
        except Exception:
            pass


class DashboardChartManager:
    """Manages individual charts to allow seamless embedding in any frame."""
    def __init__(self):
        self.canvases = []

    def safe_destroy_all(self):
        for c in self.canvases:
            _safe_destroy_canvas(c)
        self.canvases.clear()
        gc.collect()

    def _create_base_figure(self, parent_frame, title, figsize=(5, 4)):
        """Create a figure that matches the current app theme from C[]."""
        for widget in parent_frame.winfo_children():
            widget.destroy()

        bg_color   = C.get("card",  "#1e1e1e")
        text_color = C.get("text",  "#e8e8e8")
        muted_color= C.get("muted", "#9ca3af")

        fig = Figure(figsize=figsize, dpi=96, facecolor=bg_color)
        ax  = fig.add_subplot(111)

        ax.set_facecolor(bg_color)
        ax.tick_params(colors=muted_color, labelsize=9)
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.set_title(title, color=text_color, pad=12, fontsize=10, fontweight="bold")
        return fig, ax

    def _embed_figure(self, fig, parent_frame):
        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvases.append(canvas)

    def _show_no_data(self, ax):
        bg_color   = C.get("card",  "#1e1e1e")
        muted_color= C.get("muted", "#9ca3af")
        ax.clear()
        ax.set_facecolor(bg_color)
        ax.text(0.5, 0.5, "No Data Available",
                ha="center", va="center",
                color=muted_color, fontsize=11)
        ax.set_axis_off()

    def render_cashflow_chart(self, parent_frame):
        fig, ax = self._create_base_figure(parent_frame, "Revenue Trend", figsize=(8, 4))
        data = get_daily_revenue_trend(7)

        line_color  = C.get("teal",  "#3b82f6")
        muted_color = C.get("muted", "#9ca3af")

        if not data:
            self._show_no_data(ax)
        else:
            days   = [d["day"][-5:] for d in data]
            totals = [d["total"]    for d in data]

            ax.plot(days, totals, marker="o", color=line_color,
                    linewidth=2, markersize=4, zorder=3)
            # Avoid oversized wedge fill when there are very few points.
            if len(days) > 2:
                ax.fill_between(days, totals, alpha=0.12, color=line_color)
            ax.grid(True, linestyle="--", alpha=0.15, color=muted_color)

            ax.set_xlabel("Last 7 days", color=muted_color, fontsize=8, labelpad=8)

        self._embed_figure(fig, parent_frame)

    def render_top_items_chart(self, parent_frame):
        fig, ax = self._create_base_figure(parent_frame, "Top Services", figsize=(4, 3))
        data = get_top_selling_items(5)

        bar_color   = C.get("lime",  "#22c55e")
        text_color  = C.get("text",  "#e8e8e8")
        muted_color = C.get("muted", "#9ca3af")

        if not data:
            self._show_no_data(ax)
        else:
            names = [d["name"][:13] + ".." if len(d["name"]) > 13 else d["name"]
                     for d in data]
            qtys  = [d["qty"] for d in data]

            y_pos = range(len(names))
            ax.barh(y_pos, qtys, color=bar_color, height=0.55)
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(names, color=muted_color, fontsize=9)
            ax.invert_yaxis()
            ax.grid(False)
            ax.xaxis.set_visible(False)

            for i, v in enumerate(qtys):
                ax.text(v + 0.05, i, str(v), color=text_color,
                        va="center", fontsize=9, fontweight="bold")

        self._embed_figure(fig, parent_frame)

    def render_payment_methods_chart(self, parent_frame):
        fig, ax = self._create_base_figure(parent_frame, "Revenue by Payment Mode",
                                            figsize=(4, 3))
        data = get_payment_methods_breakdown()

        text_color = C.get("text",   "#e8e8e8")
        # Use semantic theme colors for slices
        pie_colors = [
            C.get("teal",   "#3b82f6"),
            C.get("lime",   "#22c55e"),
            C.get("orange", "#f59e0b"),
            C.get("purple", "#a855f7"),
            C.get("red",    "#ef4444"),
        ]

        if not data:
            self._show_no_data(ax)
        else:
            totals = [d["total"] for d in data]
            labels = [d["method"] for d in data]

            wedges, texts, autotexts = ax.pie(
                totals,
                labels=None,
                autopct="%1.0f%%",
                colors=pie_colors[:len(totals)],
                wedgeprops=dict(width=0.42),
                startangle=90,
            )
            for autotext in autotexts:
                autotext.set_fontweight("bold")
                autotext.set_color(text_color)
                autotext.set_fontsize(9)

            # Center label
            ax.text(0, 0, "Payments", ha="center", va="center",
                    color=text_color, fontsize=9, fontweight="bold")

            # Side legend
            ax.legend(wedges, labels,
                      loc="lower center", bbox_to_anchor=(0.5, -0.15),
                      ncol=3, frameon=False,
                      fontsize=8,
                      labelcolor=text_color)

        self._embed_figure(fig, parent_frame)
