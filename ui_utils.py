# -*- coding: utf-8 -*-
"""
Shared UI helpers.
"""
import tkinter as tk


def make_searchable_combobox(combo, full_list):
    """Attach lightweight live search/autocomplete behavior to a ttk.Combobox."""
    items = []
    seen = set()
    for item in full_list or []:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)

    if getattr(combo, "_searchable_initialized", False):
        combo._searchable_full_list = items[:]
        combo._searchable_filtered = items[:20]
        combo["values"] = combo._searchable_filtered
        return combo
    combo._searchable_initialized = True

    combo._searchable_full_list = items
    combo._searchable_filtered = items[:20]
    after_id = None

    try:
        if str(combo.cget("state")) == "readonly":
            combo.configure(state="normal")
    except Exception:
        pass

    def _source_items():
        return list(getattr(combo, "_searchable_full_list", items))

    def _filter_values(query):
        q = (query or "").strip().lower()
        if not q:
            return _source_items()[:20]
        return [item for item in _source_items() if q in item.lower()][:20]

    def _refresh(query="", open_dropdown=False):
        filtered = _filter_values(query)
        combo._searchable_filtered = filtered
        combo["values"] = filtered
        if open_dropdown and filtered:
            try:
                combo.event_generate("<Down>")
            except Exception:
                pass
        return filtered

    def _run_filter(open_dropdown=False):
        nonlocal after_id
        after_id = None
        typed = combo.get()
        filtered = _refresh(typed, open_dropdown=open_dropdown and bool(typed.strip()))
        if filtered:
            try:
                combo.current(0)
            except Exception:
                pass
        return filtered

    def _on_keyrelease(event):
        nonlocal after_id
        if getattr(event, "keysym", "") in {"Up", "Down", "Return", "Escape", "Tab"}:
            return
        if after_id is not None:
            try:
                combo.after_cancel(after_id)
            except Exception:
                pass
        after_id = combo.after(150, lambda: _run_filter(open_dropdown=True))

    def _on_focusin(event):
        _run_filter(open_dropdown=bool(combo.get().strip()))

    def _show_all_values(event=None):
        _refresh("", open_dropdown=False)
        combo._searchable_show_all_next = True

    def _on_button_click(event):
        try:
            if int(getattr(event, "x", 0)) >= max(0, combo.winfo_width() - 28):
                _show_all_values(event)
        except Exception:
            pass

    def _on_postcommand():
        try:
            if getattr(combo, "_searchable_show_all_next", False):
                combo._searchable_show_all_next = False
                _refresh("", open_dropdown=False)
                return
            _refresh(combo.get(), open_dropdown=False)
        except Exception:
            pass

    def _on_return(event):
        filtered = getattr(combo, "_searchable_filtered", None) or _filter_values(combo.get())
        if not filtered:
            return "break"
        typed = combo.get().strip().lower()
        chosen = next((item for item in filtered if item.lower() == typed), filtered[0])
        combo.set(chosen)
        try:
            combo.icursor(tk.END)
        except Exception:
            pass
        combo.event_generate("<<ComboboxSelected>>")
        return "break"

    if not getattr(combo, "_searchable_bound", False):
        combo.bind("<KeyRelease>", _on_keyrelease, add="+")
        combo.bind("<FocusIn>", _on_focusin, add="+")
        combo.bind("<Return>", _on_return, add="+")
        combo.bind("<Button-1>", _on_button_click, add="+")
        combo.bind("<F4>", _show_all_values, add="+")
        combo.bind("<Alt-Down>", _show_all_values, add="+")
        try:
            combo.configure(postcommand=_on_postcommand)
        except Exception:
            pass
        combo._searchable_bound = True

    combo["values"] = combo._searchable_filtered
    return combo
