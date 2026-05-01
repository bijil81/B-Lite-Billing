# -*- coding: utf-8 -*-
"""
offers.py  –  BOBY'S Salon : Offer & Discount Management
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import os
from utils import (C, load_json, safe_float,
                   fmt_currency, now_str, today_str, DATA_DIR,
                   popup_window, app_log)
from date_helpers import attach_date_mask, display_to_iso_date, iso_to_display_date, today_display_str, validate_display_date
from ui_theme import apply_treeview_column_alignment, ModernButton, ensure_segoe_ttk_font
from icon_system import get_action_icon
from services_v5.offers_service import OffersService
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready

F_OFFERS = os.path.join(DATA_DIR, "offers.json")

_OFFERS_SERVICE = OffersService()


def fix_mojibake(text):
    text = "" if text is None else str(text)
    candidates = [text]
    try:
        candidates.append(text.encode("latin1").decode("utf-8"))
    except Exception:
        pass
    try:
        candidates.append(text.encode("cp1252").decode("utf-8"))
    except Exception:
        pass
    markers = ("Ã", "â", "ð", "�")
    for value in candidates:
        if not any(marker in value for marker in markers):
            return value
    return candidates[-1]


def safe_text(text):
    return fix_mojibake(text).strip()


def _clean_offer_payload(offer: dict) -> dict:
    return {
        **offer,
        "name": safe_text(offer.get("name", "")),
        "type": safe_text(offer.get("type", "percentage")) or "percentage",
        "service_name": safe_text(offer.get("service_name", "")),
        "coupon_code": safe_text(offer.get("coupon_code", "")).upper(),
        "description": safe_text(offer.get("description", "")),
    }


def _clean_offer_list(offers: list[dict]) -> tuple[list[dict], bool]:
    cleaned = []
    changed = False
    for offer in offers:
        clean = _clean_offer_payload(offer)
        cleaned.append(clean)
        if clean != offer:
            changed = True
    return cleaned, changed


def _load_legacy_offers() -> list:
    offers = load_json(F_OFFERS, [])
    cleaned, _ = _clean_offer_list(offers)
    return cleaned


def get_offers() -> list:
    offers = _OFFERS_SERVICE.get_all()
    if offers:
        cleaned, changed = _clean_offer_list(offers)
        if changed:
            _OFFERS_SERVICE.save_all(cleaned)
        return cleaned
    return _load_legacy_offers()


def save_offers(data: list) -> bool:
    cleaned, _ = _clean_offer_list(data)
    _OFFERS_SERVICE.save_all(cleaned)
    return True


def get_active_offers() -> list:
    td = today_str()
    offers = _OFFERS_SERVICE.get_active(td)
    if offers:
        cleaned, changed = _clean_offer_list(offers)
        if changed:
            _OFFERS_SERVICE.save_all(get_offers())
        return cleaned
    result = []
    for o in _load_legacy_offers():
        if not o.get("active", True):
            continue
        start = o.get("valid_from", "2000-01-01")
        end = o.get("valid_to", "2099-12-31")
        if start <= td <= end:
            result.append(o)
    return result


def apply_offer(offer: dict, bill_items: list, subtotal: float) -> float:
    offer = _clean_offer_payload(offer)
    otype = offer.get("type", "percentage")

    if otype == "percentage":
        pct = safe_float(offer.get("value", 0))
        return round(subtotal * pct / 100, 2)

    elif otype == "flat":
        return min(safe_float(offer.get("value", 0)), subtotal)

    elif otype == "service_wise":
        svc_name = offer.get("service_name", "").lower()
        pct = safe_float(offer.get("value", 0))
        total_disc = 0.0
        for it in bill_items:
            if it.get("mode") == "services" and svc_name in it.get("name", "").lower():
                total_disc += it["price"] * it["qty"] * pct / 100
        return round(total_disc, 2)

    return 0.0


def find_coupon(code: str):
    offer = _OFFERS_SERVICE.find_coupon(code, today_str())
    if offer:
        clean = _clean_offer_payload(offer)
        if clean != offer:
            _OFFERS_SERVICE.save_offer(clean)
        return clean
    target = str(code or "").strip().upper()
    if not target:
        return None
    td = today_str()
    for o in _load_legacy_offers():
        if not o.get("active", True):
            continue
        if o.get("coupon_code", "").upper() == target:
            start = o.get("valid_from", "2000-01-01")
            end = o.get("valid_to", "2099-12-31")
            if start <= td <= end:
                return _clean_offer_payload(o)
    return None

class OffersFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _rbac_denied(self) -> bool:
        if self.app.has_permission("manage_offers"):
            return False
        messagebox.showerror("Access Denied",
                             "Offer management is restricted for your role.")
        return True

    def _build(self):
        ensure_segoe_ttk_font()
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Offers & Discounts",
                 font=("Segoe UI", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Create & manage discount offers and coupons",
                 font=("Segoe UI", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w")
        ModernButton(hdr, text="Load Templates", image=get_action_icon("import_json"), compound="left",
                     command=self._load_offer_templates,
                     color=C["purple"], hover_color="#6c3483",
                     width=148, height=34, radius=8,
                     font=("Segoe UI", 10, "bold"),
                     ).pack(side=tk.RIGHT, padx=(0,6), pady=6)
        ModernButton(hdr, text="Create Offer", image=get_action_icon("add"), compound="left",
                     command=self._add_dialog,
                     color=C["teal"], hover_color=C["blue"],
                     width=138, height=34, radius=8,
                     font=("Segoe UI", 10, "bold"),
                     ).pack(side=tk.RIGHT, padx=10, pady=6)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=8)

        intro = tk.Frame(top_band, bg=C["card"], padx=18, pady=12)
        intro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(intro, text="Offers Workspace",
                 font=("Segoe UI", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro,
                 text="Review active campaigns, manage coupons, and control discount rules from one focused screen.",
                 font=("Segoe UI", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(4, 0))

        self.cards_f = tk.Frame(top_band, bg=C["bg"])
        self.cards_f.pack(side=tk.RIGHT, padx=(10, 0))

        filter_card = tk.Frame(self, bg=C["card"])
        filter_card.pack(fill=tk.X, padx=15, pady=(0, 8))
        filter_hdr = tk.Frame(filter_card, bg=C.get("nav", C["card"]))
        filter_hdr.pack(fill=tk.X)
        tk.Label(filter_hdr, text="Offer Filters",
                 font=("Segoe UI", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(filter_hdr, text="Switch between live, expired, and inactive offers",
                 font=("Segoe UI", 10),
                 bg=C.get("nav", C["card"]), fg=C["muted"]).pack(side=tk.RIGHT, padx=14, pady=8)

        ff = tk.Frame(filter_card, bg=C["card"], pady=10, padx=12)
        ff.pack(fill=tk.X)

        self.show_var = tk.StringVar(value="all")
        for txt, val in [("All", "all"),
                          ("Active", "active"),
                          ("Expired", "expired"),
                          ("Inactive", "inactive")]:
            tk.Radiobutton(ff, text=txt,
                           variable=self.show_var, value=val,
                           bg=C["card"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Segoe UI", 10),
                           command=self._load,
                           cursor="hand2").pack(side=tk.LEFT, padx=(0, 14))

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 8))

        table_card = tk.Frame(body, bg=C["card"])
        table_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        table_hdr = tk.Frame(table_card, bg=C.get("nav", C["card"]))
        table_hdr.pack(fill=tk.X)
        tk.Label(table_hdr, text="Offer Directory",
                 font=("Segoe UI", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(table_hdr, text="Double click any offer to edit details",
                 font=("Segoe UI", 10),
                 bg=C.get("nav", C["card"]), fg=C["muted"]).pack(side=tk.RIGHT, padx=14, pady=8)

        table_body = tk.Frame(table_card, bg=C["card"])
        table_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        cols = ("Name", "Type", "Value", "Coupon",
                "Valid From", "Valid To", "Status")
        self.tree = ttk.Treeview(table_body, columns=cols,
                                 show="headings", height=16)
        widths = [200, 120, 100, 120, 100, 100, 80]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)

        apply_treeview_column_alignment(self.tree)

        vsb = ttk.Scrollbar(table_body, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))

        rail = tk.Frame(body, bg=C["card"], width=220)
        rail.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
        rail.pack_propagate(False)

        rail_hdr = tk.Frame(rail, bg=C.get("nav", C["card"]))
        rail_hdr.pack(fill=tk.X)
        tk.Label(rail_hdr, text="Actions",
                 font=("Segoe UI", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(rail, text="Select an offer in the list and use these actions.",
                 justify="left", wraplength=180,
                 font=("Segoe UI", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w", padx=14, pady=(16, 18))

        bb = tk.Frame(rail, bg=C["card"])
        bb.pack(fill=tk.X, padx=12)
        for txt, icon_name, clr, hclr, cmd in [
            ("Edit",          "edit",    C["blue"],   "#154360",  self._edit_dialog),
            ("Toggle Active", "refresh", C["orange"], "#d35400",  self._toggle),
            ("Delete",        "delete",  C["red"],    "#c0392b",  self._delete),
        ]:
            ModernButton(bb, text=txt, image=get_action_icon(icon_name), compound="left", command=cmd,
                         color=clr, hover_color=hclr,
                         width=180, height=38, radius=8,
                         font=("Segoe UI", 10, "bold"),
                         ).pack(fill=tk.X, pady=5)

        self.tree.bind("<Double-1>", lambda _e: self._edit_dialog())
        self._load()

    def _load(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        offers   = get_offers()
        td       = today_str()
        active_c = expired_c = inactive_c = 0
        flt      = self.show_var.get()

        for o in offers:
            start  = o.get("valid_from", "2000-01-01")
            end    = o.get("valid_to",   "2099-12-31")
            active = o.get("active", True)

            if not active:
                status = "Inactive"; inactive_c += 1
            elif td > end:
                status = "Expired";   expired_c += 1
            elif td < start:
                status = "Active"; active_c += 1
            else:
                status = "Active"; active_c += 1

            if flt == "active"   and status != "Active": continue
            if flt == "expired"  and status != "Expired":   continue
            if flt == "inactive" and status != "Inactive":  continue

            vtype  = o.get("type", "percentage")
            val    = safe_float(o.get("value", 0))
            val_s  = (f"{val:.0f}%" if vtype == "percentage"
                      else (f"Rs{val:.0f}" if vtype == "flat"
                            else f"{val:.0f}% on service"))

            self.tree.insert("", tk.END, values=(
                o.get("name", ""),
                vtype.replace("_", " ").title(),
                val_s,
                o.get("coupon_code", "-"),
                iso_to_display_date(o.get("valid_from", "")),
                iso_to_display_date(o.get("valid_to", "")),
                status,
            ))

        # Cards
        for w in self.cards_f.winfo_children():
            w.destroy()
        for lbl, val, col in [
            ("Active Offers",   str(active_c),   C["teal"]),
            ("Expired",         str(expired_c),  C["muted"]),
            ("Inactive",        str(inactive_c), C["sidebar"]),
            ("Total Offers",    str(len(offers)), C["blue"]),
        ]:
            card = tk.Frame(self.cards_f, bg=col, padx=18, pady=8)
            card.pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(card, text=val,
                     font=("Segoe UI", 14, "bold"),
                     bg=col, fg="white").pack()
            tk.Label(card, text=lbl,
                     font=("Segoe UI", 10),
                     bg=col, fg="white").pack()

    def _offer_form(self, title: str, offer: dict = None):
        o   = offer or {}
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title(title)
        popup_window(win, 580, 660)
        win.configure(bg=C["bg"])
        win.minsize(520, 500)
        win.resizable(True, True)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win.grab_release(), win.destroy()))

        tk.Label(win, text=title,
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(15, 5))

        # Scrollable body
        canvas = tk.Canvas(win, bg=C["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(win, orient="vertical",
                                command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)
        f = tk.Frame(canvas, bg=C["bg"], padx=30)
        cw = canvas.create_window((0, 0), window=f, anchor="nw")
        f.bind("<Configure>",
               lambda e: canvas.configure(
                   scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(cw, width=e.width))

        def row(lbl, widget_fn):
            tk.Label(f, text=lbl, bg=C["bg"],
                     fg=C["muted"],
                     font=("Segoe UI", 12, "bold")).pack(anchor="w",
                                                       pady=(8, 2))
            return widget_fn()

        # Offer Name
        def _name():
            e = tk.Entry(f, font=("Segoe UI", 11),
                         bg=C["input"], fg=C["text"],
                         bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6)
            e.insert(0, o.get("name", ""))
            return e
        name_ent = row("Offer Name:", _name)

        # Type
        def _type():
            var = tk.StringVar(value=o.get("type", "percentage"))
            fr  = tk.Frame(f, bg=C["bg"])
            fr.pack(fill=tk.X)
            for txt, val in [
                ("% Percentage",      "percentage"),
                ("Rs Flat Amount",     "flat"),
                ("Service-wise %", "service_wise"),
            ]:
                tk.Radiobutton(fr, text=txt, variable=var, value=val,
                               bg=C["bg"], fg=C["text"],
                               selectcolor=C["input"],
                               font=("Segoe UI", 10),
                               cursor="hand2").pack(side=tk.LEFT,
                                                    padx=(0, 12))
            return var
        type_var = row("Discount Type:", _type)

        # Value
        def _val():
            e = tk.Entry(f, font=("Segoe UI", 11),
                         bg=C["input"], fg=C["lime"],
                         bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6)
            e.insert(0, str(o.get("value", "")))
            return e
        val_ent = row("Value (% or Rs):", _val)

        # Service name (for service-wise)
        def _svc():
            e = tk.Entry(f, font=("Segoe UI", 11),
                         bg=C["input"], fg=C["text"],
                         bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6)
            e.insert(0, o.get("service_name", ""))
            tk.Label(f, text="(e.g. 'Facial' - partial name ok)",
                     bg=C["bg"], fg=C["muted"],
                     font=("Segoe UI", 10)).pack(anchor="w")
            return e
        svc_ent = row("Service Name (for service-wise):", _svc)

        # Coupon Code
        def _coupon():
            e = tk.Entry(f, font=("Segoe UI", 11),
                         bg=C["input"], fg=C["gold"],
                         bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=6)
            e.insert(0, o.get("coupon_code", ""))
            tk.Label(f,
                     text="(Optional - leave blank for dropdown-only offer)",
                     bg=C["bg"], fg=C["muted"],
                     font=("Segoe UI", 10)).pack(anchor="w")
            return e
        coupon_ent = row("Coupon Code (optional):", _coupon)

        # Date range
        dr = tk.Frame(f, bg=C["bg"])
        dr.pack(fill=tk.X, pady=(10, 0))

        tk.Label(f, text="Valid From:", bg=C["bg"],
                 fg=C["muted"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w",
                                                   pady=(8, 2))
        from_ent = tk.Entry(f, font=("Segoe UI", 11),
                             bg=C["input"], fg=C["text"],
                             bd=0, insertbackground=C["accent"])
        from_ent.pack(fill=tk.X, ipady=6)
        from_ent.insert(0, iso_to_display_date(o.get("valid_from", today_str())))
        attach_date_mask(from_ent)

        tk.Label(f, text="Valid To:", bg=C["bg"],
                 fg=C["muted"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w",
                                                   pady=(8, 2))
        to_ent = tk.Entry(f, font=("Segoe UI", 11),
                           bg=C["input"], fg=C["text"],
                           bd=0, insertbackground=C["accent"])
        to_ent.pack(fill=tk.X, ipady=6)
        to_ent.insert(0, iso_to_display_date(o.get("valid_to", "2099-12-31")))
        attach_date_mask(to_ent)

        # Description
        tk.Label(f, text="Description (optional):",
                 bg=C["bg"], fg=C["muted"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w",
                                                   pady=(8, 2))
        desc_txt = tk.Text(f, font=("Segoe UI", 11),
                            bg=C["input"], fg=C["text"],
                            bd=0, height=3,
                            insertbackground=C["accent"])
        desc_txt.pack(fill=tk.X)
        desc_txt.insert("1.0", o.get("description", ""))

        # Active toggle
        active_var = tk.BooleanVar(value=o.get("active", True))
        tk.Checkbutton(f, text="Active (show in billing dropdown)",
                       variable=active_var,
                       bg=C["bg"], fg=C["text"],
                       selectcolor=C["input"],
                       font=("Segoe UI", 10),
                       cursor="hand2").pack(anchor="w", pady=(12, 0))

        def _save():
            nm  = name_ent.get().strip()
            val = val_ent.get().strip()
            if not nm:
                messagebox.showerror("Error", "Enter offer name.");
                return
            try:
                fv = float(val)
                if fv <= 0: raise ValueError
            except Exception:
                messagebox.showerror("Error", "Enter valid value (> 0).")
                return
            from_raw = from_ent.get().strip() or today_display_str()
            to_raw = to_ent.get().strip() or "31-12-2099"
            if not validate_display_date(from_raw) or not validate_display_date(to_raw):
                messagebox.showerror("Error", "Offer dates must be DD-MM-YYYY format.\nExample: 15-06-2026")
                return

            new_offer = {
                "name":         nm,
                "type":         type_var.get(),
                "value":        fv,
                "service_name": svc_ent.get().strip(),
                "coupon_code":  coupon_ent.get().strip().upper(),
                "valid_from":   display_to_iso_date(from_raw),
                "valid_to":     display_to_iso_date(to_raw),
                "description":  desc_txt.get("1.0", tk.END).strip(),
                "active":       active_var.get(),
                "created":      o.get("created", now_str()),
            }

            offers = get_offers()
            if offer is not None:
                # Edit: replace existing
                idx = next((i for i, x in enumerate(offers)
                             if x.get("name") == o.get("name")), None)
                if idx is not None:
                    offers[idx] = new_offer
                else:
                    offers.append(new_offer)
            else:
                offers.append(new_offer)

            save_offers(offers)
            win.destroy()
            self._load()
            messagebox.showinfo("Saved", f"Offer '{nm}' saved!")

        ModernButton(f, text="Save Offer", image=get_action_icon("save"), compound="left",
                     command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=380, height=40, radius=8,
                     font=("Segoe UI", 11, "bold"),
                     ).pack(fill=tk.X, pady=(16, 0))
        reveal_when_ready(win)

    def _get_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an offer.")
            return None, None
        v      = self.tree.item(sel[0], "values")
        name   = v[0]
        offers = get_offers()
        obj    = next((o for o in offers
                        if o.get("name") == name), None)
        return name, obj

    def _add_dialog(self):
        if self._rbac_denied(): return
        self._offer_form("Create New Offer")

    def _edit_dialog(self):
        if self._rbac_denied(): return
        name, obj = self._get_selected()
        if not obj: return
        self._offer_form(f"Edit Offer: {name}", obj)

    def _toggle(self):
        name, obj = self._get_selected()
        if not obj: return
        from datetime import date
        td = date.today().strftime("%Y-%m-%d")
        offers = get_offers()
        for o in offers:
            if o.get("name") == name:
                currently_active = o.get("active", True)
                o["active"] = not currently_active
                # If activating, fix expired valid_to to 1 year from today
                if o["active"]:
                    end = o.get("valid_to", "2099-12-31")
                    if end < td:
                        o["valid_to"] = date.today().replace(
                            year=date.today().year + 1
                        ).strftime("%Y-%m-%d")
                break
        save_offers(offers)
        self._load()

    def _delete(self):
        if self._rbac_denied(): return
        name, obj = self._get_selected()
        if not obj: return
        if messagebox.askyesno("Delete",
                                f"Delete offer '{name}'?"):
            offers = [o for o in get_offers()
                       if o.get("name") != name]
            save_offers(offers)
            self._load()

    def _load_offer_templates(self):
        from tkinter import filedialog
        import json
        from datetime import date
        path = filedialog.askopenfilename(
            title="Select Offers Templates JSON",
            filetypes=[("JSON files","*.json"),("All","*.*")])
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                messagebox.showerror("Error","File must be a JSON array."); return
            existing = get_offers()
            names    = {o.get("name","") for o in existing}
            added    = 0
            today    = date.today().strftime("%Y-%m-%d")
            for t in data:
                if t.get("name","") not in names:
                    t.setdefault("created", today)
                    t.setdefault("active", True)
                    existing.append(t)
                    added += 1
            save_offers(existing)
            self._load()
            messagebox.showinfo("Done",
                str(added) + " offers loaded! (" +
                str(len(data)-added) + " already existed)")
        except Exception as e:
            messagebox.showerror("Error", "Could not load: " + str(e))

    def refresh(self):
        self._load()





