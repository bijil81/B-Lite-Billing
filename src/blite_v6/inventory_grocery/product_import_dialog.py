"""Preview-only product import dialog for Inventory."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Mapping

from icon_system import get_action_icon
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready
from src.blite_v6.inventory_grocery.product_import_apply import apply_import_preview
from src.blite_v6.inventory_grocery.product_import import (
    build_import_preview,
    default_column_mapping,
    parse_import_file,
)
from ui_responsive import make_scrollable
from ui_theme import ModernButton
from utils import C, popup_window


def open_product_import_preview_dialog(
    parent: tk.Misc,
    *,
    get_inventory_fn: Callable[[], Mapping[str, object]],
    save_inventory_fn: Callable[[dict], object],
    refresh_inventory_fn: Callable[[], object] | None = None,
) -> tk.Toplevel:
    """Open the G6 product import dialog with preview-first apply."""
    win = tk.Toplevel(parent)
    hide_while_building(win)
    win.title("Import Products Preview")
    popup_window(win, 980, 760)
    win.configure(bg=C["bg"])
    try:
        win.minsize(860, 640)
        win.resizable(True, True)
    except Exception:
        pass

    raw_rows: list[dict[str, object]] = []
    headers: list[str] = []
    mapping_widgets: dict[str, ttk.Combobox] = {}
    file_path_var = tk.StringVar()
    duplicate_policy = tk.StringVar(value="skip")
    below_cost_policy = tk.StringVar(value="warn")
    summary_var = tk.StringVar(value="Choose CSV, XLSX, or JSON file to preview.")
    preview_state = {"preview": None}

    def _close(event=None):
        try:
            if win.grab_current() == win:
                win.grab_release()
        except Exception:
            pass
        try:
            win.destroy()
        except Exception:
            pass

    header = tk.Frame(win, bg=C["card"], padx=18, pady=12)
    header.pack(fill=tk.X)
    tk.Label(
        header,
        text="Import Products Preview",
        bg=C["card"],
        fg=C["text"],
        font=("Arial", 14, "bold"),
    ).pack(anchor="w")
    tk.Label(
        header,
        text="Map supplier columns and validate rows before importing.",
        bg=C["card"],
        fg=C["muted"],
        font=("Arial", 10),
    ).pack(anchor="w", pady=(3, 0))

    actions = tk.Frame(win, bg=C["card"], padx=18, pady=10)
    actions.pack(fill=tk.X, side=tk.BOTTOM)

    body, canvas, _container = make_scrollable(win, bg=C["bg"], padx=18, pady=12)

    def _scroll_import_form(event):
        try:
            step = -1 if int(getattr(event, "delta", 0) or 0) > 0 else 1
            canvas.yview_scroll(step, "units")
            return "break"
        except Exception:
            return None

    def _bind_import_scroll(widget):
        try:
            widget.bind("<MouseWheel>", _scroll_import_form, add="+")
        except Exception:
            pass

    file_row = tk.Frame(body, bg=C["bg"])
    file_row.pack(fill=tk.X)
    file_row.grid_columnconfigure(1, weight=1)
    tk.Label(
        file_row,
        text="File:",
        bg=C["bg"],
        fg=C["muted"],
        font=("Arial", 11, "bold"),
    ).grid(row=0, column=0, sticky="w", padx=(0, 8))
    file_entry = tk.Entry(
        file_row,
        textvariable=file_path_var,
        font=("Arial", 10),
        bg=C["input"],
        fg=C["text"],
        bd=0,
        insertbackground=C["accent"],
    )
    file_entry.grid(row=0, column=1, sticky="ew", ipady=6, padx=(0, 8))
    _bind_import_scroll(file_entry)

    policy_row = tk.Frame(body, bg=C["bg"])
    policy_row.pack(fill=tk.X, pady=(10, 4))
    tk.Label(
        policy_row,
        text="Existing Items:",
        bg=C["bg"],
        fg=C["muted"],
        font=("Arial", 10, "bold"),
    ).pack(side=tk.LEFT, padx=(0, 6))
    duplicate_combo = ttk.Combobox(
        policy_row,
        textvariable=duplicate_policy,
        values=["skip", "update", "error"],
        state="readonly",
        width=10,
        font=("Arial", 10),
    )
    duplicate_combo.pack(side=tk.LEFT, padx=(0, 14))
    _bind_import_scroll(duplicate_combo)
    tk.Label(
        policy_row,
        text="Below Cost:",
        bg=C["bg"],
        fg=C["muted"],
        font=("Arial", 10, "bold"),
    ).pack(side=tk.LEFT, padx=(0, 6))
    below_cost_combo = ttk.Combobox(
        policy_row,
        textvariable=below_cost_policy,
        values=["warn", "error", "allow"],
        state="readonly",
        width=10,
        font=("Arial", 10),
    )
    below_cost_combo.pack(side=tk.LEFT)
    _bind_import_scroll(below_cost_combo)

    mapping_box = tk.Frame(body, bg=C["card"], padx=12, pady=10)
    mapping_box.pack(fill=tk.X, pady=(10, 8))
    tk.Label(
        mapping_box,
        text="Column Mapping",
        bg=C["card"],
        fg=C["text"],
        font=("Arial", 11, "bold"),
    ).pack(anchor="w")

    mapping_grid = tk.Frame(mapping_box, bg=C["card"])
    mapping_grid.pack(fill=tk.X, pady=(8, 0))
    mapping_fields = [
        ("name", "Product Name *"),
        ("category", "Category *"),
        ("sale_price", "Sale Price *"),
        ("cost", "Cost Price"),
        ("qty", "Opening Stock"),
        ("unit", "Unit"),
        ("barcode", "Barcode"),
        ("sku", "SKU"),
        ("gst_rate", "GST Rate %"),
        ("hsn_sac", "HSN/SAC"),
        ("mrp", "MRP"),
        ("brand", "Brand"),
    ]

    for idx, (field_name, label) in enumerate(mapping_fields):
        row = idx // 2
        col = (idx % 2) * 2
        tk.Label(
            mapping_grid,
            text=label,
            bg=C["card"],
            fg=C["muted"],
            font=("Arial", 9),
        ).grid(row=row, column=col, sticky="w", padx=(0, 6), pady=4)
        var = tk.StringVar()
        combo = ttk.Combobox(mapping_grid, textvariable=var, values=[], font=("Arial", 9), width=20)
        combo.grid(row=row, column=col + 1, sticky="ew", padx=(0, 12), pady=4)
        _bind_import_scroll(combo)
        mapping_widgets[field_name] = combo
    for col in (1, 3):
        mapping_grid.grid_columnconfigure(col, weight=1)

    summary = tk.Label(
        body,
        textvariable=summary_var,
        bg=C["bg"],
        fg=C["muted"],
        font=("Arial", 10),
        anchor="w",
        justify="left",
    )
    summary.pack(fill=tk.X, pady=(4, 8))

    preview_box = tk.Frame(body, bg=C["card"])
    preview_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
    preview_head = tk.Frame(preview_box, bg=C["sidebar"], padx=10, pady=6)
    preview_head.pack(fill=tk.X)
    tk.Label(
        preview_head,
        text="Preview",
        bg=C["sidebar"],
        fg=C["text"],
        font=("Arial", 11, "bold"),
    ).pack(side=tk.LEFT)
    tk.Label(
        preview_head,
        text="Preview before import",
        bg=C["sidebar"],
        fg=C["muted"],
        font=("Arial", 9),
    ).pack(side=tk.RIGHT)
    tk.Frame(preview_box, bg=C["blue"], height=2).pack(fill=tk.X)
    tree_wrap = tk.Frame(preview_box, bg=C["card"], padx=10, pady=10)
    tree_wrap.pack(fill=tk.BOTH, expand=True)
    cols = ("Row", "Action", "Item", "Category", "Price", "Issues")
    preview_tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", height=10)
    for col, width in zip(cols, [60, 90, 220, 140, 90, 360]):
        preview_tree.heading(col, text=col)
        preview_tree.column(col, width=width, minwidth=50)
    vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=preview_tree.yview)
    preview_tree.configure(yscrollcommand=vsb.set)
    preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    _bind_import_scroll(preview_tree)

    def _set_mapping_values(defaults=None):
        values = [""] + headers
        defaults = defaults or {}
        for field_name, combo in mapping_widgets.items():
            combo["values"] = values
            combo.set(defaults.get(field_name, ""))

    def _collect_mapping():
        return {
            field_name: combo.get().strip()
            for field_name, combo in mapping_widgets.items()
            if combo.get().strip()
        }

    def _render_preview():
        for item_id in preview_tree.get_children():
            preview_tree.delete(item_id)
        if not raw_rows:
            summary_var.set("Choose a file before preview.")
            preview_state["preview"] = None
            return
        preview = build_import_preview(
            raw_rows,
            column_mapping=_collect_mapping(),
            existing_items=get_inventory_fn(),
            duplicate_policy=duplicate_policy.get(),
            below_cost_policy=below_cost_policy.get(),
        )
        preview_state["preview"] = preview
        for row in preview.rows:
            issue_text = "; ".join(
                [issue.message for issue in row.errors]
                + [warning.message for warning in row.warnings]
            )
            preview_tree.insert(
                "",
                tk.END,
                values=(
                    row.row_number,
                    row.action.upper(),
                    row.mapped.get("name", ""),
                    row.mapped.get("category", ""),
                    row.mapped.get("sale_price", ""),
                    issue_text,
                ),
            )
        summary_var.set(
            f"Rows: {len(preview.rows)} | Create: {preview.created_count} | "
            f"Update: {preview.updated_count} | Skip: {preview.skipped_count} | "
            f"Errors: {preview.error_count} | Warnings: {preview.warning_count}"
        )

    def _apply_preview():
        preview = preview_state.get("preview")
        if preview is None:
            _render_preview()
            preview = preview_state.get("preview")
        if preview is None:
            messagebox.showwarning("Import Products", "Choose a file and preview rows first.")
            return
        valid_count = preview.created_count + preview.updated_count
        if valid_count <= 0:
            messagebox.showwarning("Import Products", "There are no create/update rows to import.")
            return
        if preview.error_count:
            if not messagebox.askyesno(
                "Import Valid Rows",
                f"{preview.error_count} row error(s) will be skipped.\n\n"
                f"Import {valid_count} valid row(s)?",
                default="no",
            ):
                return
        elif preview.warning_count:
            if not messagebox.askyesno(
                "Import Products",
                f"{preview.warning_count} warning(s) found.\n\n"
                f"Import {valid_count} row(s)?",
                default="no",
            ):
                return
        result = apply_import_preview(
            preview,
            existing_inventory=get_inventory_fn(),
            save_inventory_fn=save_inventory_fn,
            source_file=file_path_var.get(),
        )
        if refresh_inventory_fn is not None:
            try:
                refresh_inventory_fn()
            except Exception:
                pass
        message = (
            f"Created: {result.created_count}\n"
            f"Updated: {result.updated_count}\n"
            f"Skipped: {result.skipped_count}\n"
            f"Errors: {result.error_count}\n\n"
            f"Batch: {result.batch_id}"
        )
        if result.error_count:
            error_lines = [
                f"Row {row.row_number}: {row.message}"
                for row in result.rows
                if row.status == "error" and row.message
            ][:5]
            if error_lines:
                message += "\n\n" + "\n".join(error_lines)
            messagebox.showwarning("Import Completed With Issues", message)
        else:
            messagebox.showinfo("Import Completed", message)
            _close()

    def _choose_file():
        path = filedialog.askopenfilename(
            title="Choose product import file",
            filetypes=[
                ("Product import files", "*.csv *.xlsx *.json"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("JSON", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            loaded_rows = parse_import_file(path)
        except Exception as exc:
            messagebox.showerror("Import Preview", f"Could not read file:\n{exc}")
            return
        raw_rows.clear()
        raw_rows.extend(loaded_rows)
        headers.clear()
        for row in raw_rows:
            for header in row.keys():
                text = str(header)
                if text not in headers:
                    headers.append(text)
        file_path_var.set(path)
        _set_mapping_values(default_column_mapping(headers))
        _render_preview()

    browse_button = ModernButton(
        file_row,
        text="Browse",
        image=get_action_icon("browse"),
        compound="left",
        command=_choose_file,
        color=C["blue"],
        hover_color=C["teal"],
        width=110,
        height=32,
        radius=8,
        font=("Arial", 10, "bold"),
    )
    browse_button.grid(row=0, column=2, sticky="e")

    ModernButton(
        actions,
        text="Preview",
        command=_render_preview,
        color=C["blue"],
        hover_color=C["teal"],
        width=160,
        height=38,
        radius=8,
        font=("Arial", 11, "bold"),
    ).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ModernButton(
        actions,
        text="Import Valid Rows",
        command=_apply_preview,
        color=C["teal"],
        hover_color=C["blue"],
        width=180,
        height=38,
        radius=8,
        font=("Arial", 11, "bold"),
    ).pack(side=tk.LEFT, padx=(10, 0))
    ModernButton(
        actions,
        text="Close",
        command=_close,
        color=C["sidebar"],
        hover_color=C["blue"],
        width=120,
        height=38,
        radius=8,
        font=("Arial", 11, "bold"),
    ).pack(side=tk.LEFT, padx=(10, 0))
    win.bind("<Escape>", _close)
    win.after(0, lambda: _bind_import_scroll(win))
    reveal_when_ready(win)
    return win
