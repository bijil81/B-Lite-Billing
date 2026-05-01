from __future__ import annotations

import tkinter as tk


def bind_customer_lookup_entries(owner) -> None:
    owner.name_ent.bind("<KeyRelease>", lambda event: owner._on_customer_keyrelease(event, "name"))
    owner.phone_ent.bind("<KeyRelease>", lambda event: owner._on_customer_keyrelease(event, "phone"))
    owner.name_ent.bind("<FocusOut>", lambda _event: owner.after(120, owner._hide_suggestions_if_safe))
    owner.phone_ent.bind("<FocusOut>", lambda _event: owner.after(120, owner._hide_suggestions_if_safe))
    owner.name_ent.bind("<Escape>", lambda event: owner._on_customer_escape(event))
    owner.phone_ent.bind("<Escape>", lambda event: owner._on_customer_escape(event))
    owner.name_ent.bind("<Down>", lambda event: owner._focus_suggestion(event))
    owner.phone_ent.bind("<Down>", lambda event: owner._focus_suggestion(event))
    owner.name_ent.bind("<Up>", lambda event: owner._focus_suggestion(event, move=-1))
    owner.phone_ent.bind("<Up>", lambda event: owner._focus_suggestion(event, move=-1))
    owner.name_ent.bind("<Return>", lambda event: owner._commit_customer_suggestion(event, "name"))
    owner.phone_ent.bind("<Return>", lambda event: owner._commit_customer_suggestion(event, "phone"))


def bind_search_entry(owner) -> None:
    owner.search_ent.bind("<KeyRelease>", owner._ss_typing)
    owner.search_ent.bind("<Down>", owner._ss_focus)
    owner.search_ent.bind("<Return>", owner._ss_enter)
    owner.search_ent.bind("<Escape>", lambda _event: owner._ss_hide())
    owner.search_ent.bind("<FocusIn>", lambda _event: owner._ss_on_focus())
    owner.search_ent.bind("<FocusOut>", owner._ss_on_search_focusout)


def bind_quantity_entry(owner) -> None:
    owner.qty_ent.bind("<Button-1>", lambda _event: owner.after_idle(owner._focus_qty_entry))
    owner.qty_ent.bind("<ButtonRelease-1>", lambda _event: owner.after_idle(owner._focus_qty_entry))
    owner.qty_ent.bind("<FocusIn>", lambda _event: owner.qty_ent.select_range(0, tk.END))


def bind_discount_entry(owner) -> None:
    owner.disc_ent.bind("<KeyRelease>", lambda _event: owner._refresh_bill())
    owner.disc_ent.bind("<Button-1>", lambda _event: owner.after_idle(owner._focus_discount_entry))
    owner.disc_ent.bind("<ButtonRelease-1>", lambda _event: owner.after_idle(owner._focus_discount_entry))
    owner.disc_ent.bind("<FocusIn>", lambda _event: owner.disc_ent.select_range(0, tk.END))


def bind_barcode_entry(owner) -> None:
    owner.scan_entry.bind("<Return>", owner._on_barcode_enter)
    owner.scan_entry.bind("<FocusOut>", lambda _event: owner.after(200, owner._on_scan_focus_out))


def bind_bill_preview_text(owner) -> None:
    owner.txt.bind("<Double-Button-1>", owner._edit_item_qty)
    owner.txt.bind("<Button-3>", owner._right_click_menu)
