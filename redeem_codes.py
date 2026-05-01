"""
redeem_codes.py  Ã¢â‚¬â€œ  BOBY'S Salon
Generate one-time redeem codes Ã¢â€ â€™ send to customers via WhatsApp
Ã¢â€ â€™ apply at billing Ã¢â€ â€™ auto-expire after use.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os, random, string
from datetime import datetime, date
from ui_theme import ModernButton, apply_treeview_column_alignment
from icon_system import get_action_icon
from branding import get_company_name, get_redeem_prefix
from utils import (C, load_json, save_json, safe_float,
                   fmt_currency, now_str, today_str, DATA_DIR,
                   F_CUSTOMERS, validate_phone, app_log)

F_REDEEM = os.path.join(DATA_DIR, "redeem_codes.json")


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  DATA HELPERS
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
def get_codes() -> dict:
    return load_json(F_REDEEM, {})

def save_codes(data: dict) -> bool:
    return save_json(F_REDEEM, data)

def generate_code(prefix: str = "", length: int = 5) -> str:
    """Generate unique alphanumeric code like BLITE-XK7P2"""
    chars    = string.ascii_uppercase + string.digits
    existing = set(get_codes().keys())
    prefix = (prefix or get_redeem_prefix()).upper()
    while True:
        code = prefix + "-" + "".join(
            random.choices(chars, k=length))
        if code not in existing:
            return code

def create_code(discount_type: str, value: float,
                phone: str = "", name: str = "",
                expiry: str = "", note: str = "") -> str:
    """
    Create and store a redeem code.
    discount_type: 'percentage' | 'flat'
    Returns the code string.
    """
    code  = generate_code()
    codes = get_codes()
    codes[code] = {
        "discount_type": discount_type,
        "value":         value,
        "phone":         phone,
        "name":          name,
        "expiry":        expiry or "2099-12-31",
        "note":          note,
        "used":          False,
        "used_on":       "",
        "used_invoice":  "",
        "created":       now_str(),
    }
    save_codes(codes)
    return code

def validate_code(code: str, customer_phone: str = None) -> tuple:
    """
    Returns (is_valid: bool, info: dict | str)
    If valid Ã¢â€ â€™ info = code dict
    If invalid Ã¢â€ â€™ info = error message string
    """
    code  = code.strip().upper()
    codes = get_codes()

    if code not in codes:
        return False, "Invalid code Ã¢â‚¬â€ not found."

    c = codes[code]

    if c.get("used"):
        return False, f"Already used on {c.get('used_on','')[:10]}."

    if c.get("expiry", "2099-12-31") < today_str():
        return False, "Code has expired."

    # H13 FIX: Enforce phone-based restriction
    code_phone = str(c.get("phone", c.get("customer_phone", "")) or "").strip()
    bill_phone = str(customer_phone or "").strip()
    if code_phone and not bill_phone:
        return False, "This code requires the assigned customer phone."
    if code_phone and bill_phone != code_phone:
        return False, "This code is assigned to another customer."

    return True, c

def apply_redeem_code(code: str, invoice: str, customer_phone: str = None) -> tuple:
    """
    Mark code as used. Returns (discount_type, value).

    H14 FIX: Now re-validates the code before marking as used.
    Previously this function accepted any code and blindly marked
    it as used, ignoring expired/already-used status.
    """
    # H14 FIX: Re-validate before marking as used
    valid, info = validate_code(code, customer_phone=customer_phone)
    if not valid:
        from utils import app_log
        app_log(f"[apply_redeem_code] BLOCKED: {code} -- {info}")
        return None, 0.0

    # Reload codes for mutation (validate_code has its own local copy)
    codes = get_codes()

    # Race condition guard: re-check not already used
    if codes.get(code, {}).get("used"):
        from utils import app_log
        app_log(f"[apply_redeem_code] BLOCKED: {code} already marked used")
        return None, 0.0

    codes[code]["used"]         = True
    codes[code]["used_on"]      = now_str()
    codes[code]["used_invoice"] = invoice
    save_codes(codes)

    c = codes[code]
    return c["discount_type"], safe_float(c["value"])

def calc_redeem_discount(code: str, subtotal: float, customer_phone: str = None) -> float:
    """Calculate discount amount without marking as used."""
    valid, info = validate_code(code, customer_phone=customer_phone)
    if not valid: return 0.0
    if info["discount_type"] == "percentage":
        return round(subtotal * safe_float(info["value"]) / 100, 2)
    else:
        return min(safe_float(info["value"]), subtotal)


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  REDEEM CODE FRAME (admin module)
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
class RedeemCodesFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._register_redeem_context_menu_callbacks()
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="Redeem Codes",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Generate & send discount codes to customers",
                 font=("Arial", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w")
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=8)
        intro = tk.Frame(top_band, bg=C["card"], padx=18, pady=12)
        intro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(intro, text="Redeem Workspace",
                 font=("Arial", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro, text="Create one-time codes, review history, and send offers cleanly.",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(4, 0))

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        t1 = tk.Frame(nb, bg=C["bg"])
        t2 = tk.Frame(nb, bg=C["bg"])

        nb.add(t1, text="Generate & Send")
        nb.add(t2, text="All Codes")

        self._build_generate(t1)
        self._build_list(t2)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Generate Tab Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build_generate(self, parent):
        shell = tk.Frame(parent, bg=C["bg"])
        shell.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        form_card = tk.Frame(shell, bg=C["card"])
        form_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        form_hdr = tk.Frame(form_card, bg=C.get("nav", C["card"]))
        form_hdr.pack(fill=tk.X)
        tk.Label(form_hdr, text="Generate Codes",
                 font=("Arial", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(form_hdr, text="Create one code or bulk-generate offers for customers",
                 font=("Arial", 10),
                 bg=C.get("nav", C["card"]), fg=C["muted"]).pack(side=tk.RIGHT, padx=14, pady=8)

        f = tk.Frame(form_card, bg=C["card"], padx=24, pady=18)
        f.pack(fill=tk.BOTH, expand=True)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Discount settings Ã¢â€â‚¬Ã¢â€â‚¬
        tk.Label(f, text="Discount Type:",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        self.dtype_var = tk.StringVar(value="flat")
        tr = tk.Frame(f, bg=C["card"])
        tr.pack(fill=tk.X, pady=(4, 12))
        for txt, val in [("Rs Flat Amount", "flat"),
                          ("% Percentage", "percentage")]:
            tk.Radiobutton(tr, text=txt,
                           variable=self.dtype_var, value=val,
                           bg=C["card"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 12),
                           cursor="hand2").pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(f, text="Discount Value:",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        self.val_ent = tk.Entry(f, font=("Arial", 12),
                                 bg=C["input"], fg=C["lime"],
                                 bd=0, insertbackground=C["accent"])
        self.val_ent.pack(fill=tk.X, ipady=7, pady=(4, 12))
        self.val_ent.insert(0, "100")

        tk.Label(f, text="Expiry Date (DD-MM-YYYY):",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        self.exp_ent = tk.Entry(f, font=("Arial", 12),
                                 bg=C["input"], fg=C["text"],
                                 bd=0, insertbackground=C["accent"])
        self.exp_ent.pack(fill=tk.X, ipady=7, pady=(4, 12))
        # Default: 30 days from today
        from datetime import timedelta
        default_exp = (date.today() + timedelta(days=30)
                       ).strftime("%Y-%m-%d")
        self.exp_ent.insert(0, default_exp)

        tk.Label(f, text="Note / Occasion (optional):",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        self.note_ent = tk.Entry(f, font=("Arial", 12),
                                  bg=C["input"], fg=C["text"],
                                  bd=0, insertbackground=C["accent"])
        self.note_ent.pack(fill=tk.X, ipady=7, pady=(4, 12))

        tk.Label(f, text="How many codes to generate?",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        self.count_ent = tk.Entry(f, font=("Arial", 12),
                                   bg=C["input"], fg=C["text"],
                                   bd=0, width=8,
                                   insertbackground=C["accent"])
        self.count_ent.pack(anchor="w", ipady=7, pady=(4, 16))
        self.count_ent.insert(0, "1")

        # Buttons
        br = tk.Frame(f, bg=C["card"])
        br.pack(fill=tk.X)
        ModernButton(br, text="Generate Code(s)", image=get_action_icon("add"), compound="left",
                     command=self._generate,
                     color=C["teal"], hover_color=C["blue"],
                     width=180, height=40, radius=8,
                     font=("Arial", 11, "bold"),
                     ).pack(side=tk.LEFT, padx=(0,10))
        ModernButton(br, text="Generate for All Customers", image=get_action_icon("add"), compound="left",
                     command=self._generate_for_all,
                     color=C["purple"], hover_color="#6c3483",
                     width=240, height=40, radius=8,
                     font=("Arial", 11, "bold"),
                     ).pack(side=tk.LEFT)

        # Preview / result
        self.result_lbl = tk.Label(f, text="",
                                    bg=C["card"], fg=C["gold"],
                                    font=("Arial", 13, "bold"),
                                    wraplength=500, justify="left")
        self.result_lbl.pack(anchor="w", pady=(16, 0))
        self.result_lbl.bind("<Button-3>", self._show_redeem_result_context_menu, add="+")
        self.result_lbl.bind("<Shift-F10>", self._show_redeem_result_context_menu, add="+")

        tk.Label(f,
                 text="After generating, go to 'All Codes' tab to send via WhatsApp.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 11)).pack(anchor="w", pady=(8, 0))

        side = tk.Frame(shell, bg=C["card"], width=260)
        side.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
        side.pack_propagate(False)

        side_hdr = tk.Frame(side, bg=C.get("nav", C["card"]))
        side_hdr.pack(fill=tk.X)
        tk.Label(side_hdr, text="Guidelines",
                 font=("Arial", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        for idx, note in enumerate([
            "Use flat amount for fixed-value coupons.",
            "Use percentage for reusable campaigns.",
            "Bulk generation works best for festival and loyalty drives.",
            "All codes remain available in the All Codes tab."
        ]):
            tk.Label(side, text=f"- {note}", justify="left", wraplength=210,
                     bg=C["card"], fg=C["muted"], font=("Arial", 10)).pack(anchor="w", padx=14, pady=((12 if idx == 0 else 6), 0))

    def _generate(self):
        try:
            val   = safe_float(self.val_ent.get())
            count = max(1, min(100, int(self.count_ent.get() or "1")))
            exp   = self.exp_ent.get().strip()
            note  = self.note_ent.get().strip()
            dtype = self.dtype_var.get()
        except Exception:
            messagebox.showerror("Error", "Enter valid values."); return

        if val <= 0:
            messagebox.showerror("Error", "Discount value must be > 0"); return

        codes = []
        for _ in range(count):
            code = create_code(dtype, val, expiry=exp, note=note)
            codes.append(code)

        if len(codes) == 1:
            val_s = (f"Rs{val:.0f}" if dtype == "flat"
                     else f"{val:.0f}%")
            self.result_lbl.config(
                text=f"Code: {codes[0]}\n"
                     f"Discount: {val_s}  |  Expiry: {exp}")
        else:
            self.result_lbl.config(
                text=f"{len(codes)} codes generated.\n"
                     f"Go to 'All Codes' tab to view and send.")

        self._load_list()
        messagebox.showinfo("Generated",
                             f"{len(codes)} code(s) created!\n"
                             f"Go to 'All Codes' tab to send via WhatsApp.")

    def _generate_for_all(self):
        customers = load_json(F_CUSTOMERS, {})
        active    = [(ph, c.get("name",""))
                     for ph, c in customers.items()
                     if ph and ph != "0000000000"]
        if not active:
            messagebox.showwarning("No Customers",
                                    "No customers in database."); return

        try:
            val   = safe_float(self.val_ent.get())
            exp   = self.exp_ent.get().strip()
            note  = self.note_ent.get().strip()
            dtype = self.dtype_var.get()
        except Exception:
            messagebox.showerror("Error", "Enter valid values."); return

        if not messagebox.askyesno(
                "Confirm",
                f"Generate {len(active)} codes "
                f"(one per customer)?"):
            return

        for ph, nm in active:
            create_code(dtype, val, phone=ph,
                         name=nm, expiry=exp, note=note)

        self._load_list()
        messagebox.showinfo("Done",
                             f"{len(active)} codes generated!\n"
                             f"Go to 'All Codes' tab to send.")

    # Ã¢â€â‚¬Ã¢â€â‚¬ All Codes Tab Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build_list(self, parent):
        shell = tk.Frame(parent, bg=C["bg"])
        shell.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        filter_card = tk.Frame(shell, bg=C["card"])
        filter_card.pack(fill=tk.X, pady=(0, 8))

        filter_hdr = tk.Frame(filter_card, bg=C.get("nav", C["card"]))
        filter_hdr.pack(fill=tk.X)
        tk.Label(filter_hdr, text="Code Filters",
                 font=("Arial", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(filter_hdr, text="Review unused, used, and expired codes quickly",
                 font=("Arial", 10),
                 bg=C.get("nav", C["card"]), fg=C["muted"]).pack(side=tk.RIGHT, padx=14, pady=8)

        ff = tk.Frame(filter_card, bg=C["card"], pady=10, padx=12)
        ff.pack(fill=tk.X)

        self.filter_var = tk.StringVar(value="all")
        for txt, val in [("All","all"),
                          ("Unused","unused"),
                          ("Used","used"),
                          ("Expired","expired")]:
            tk.Radiobutton(ff, text=txt,
                           variable=self.filter_var, value=val,
                           bg=C["card"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 11),
                           command=self._load_list,
                           cursor="hand2").pack(side=tk.LEFT, padx=(0, 14))

        ModernButton(ff, text="Refresh", image=get_action_icon("refresh"), compound="left",
                     command=self._load_list,
                     color=C["teal"], hover_color=C["blue"],
                     width=96, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.RIGHT)

        body = tk.Frame(shell, bg=C["bg"])
        body.pack(fill=tk.BOTH, expand=True)

        table_card = tk.Frame(body, bg=C["card"])
        table_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        table_hdr = tk.Frame(table_card, bg=C.get("nav", C["card"]))
        table_hdr.pack(fill=tk.X)
        tk.Label(table_hdr, text="Redeem Code Directory",
                 font=("Arial", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(table_hdr, text="Manage and send codes from one focused list",
                 font=("Arial", 10),
                 bg=C.get("nav", C["card"]), fg=C["muted"]).pack(side=tk.RIGHT, padx=14, pady=8)

        table_body = tk.Frame(table_card, bg=C["card"])
        table_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        cols = ("Code", "Type", "Value", "Phone",
                "Name", "Expiry", "Status")
        self.tree = ttk.Treeview(table_body, columns=cols,
                                 show="headings", height=16)
        widths = [130, 90, 80, 110, 150, 100, 80]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)
        apply_treeview_column_alignment(self.tree)

        vsb = ttk.Scrollbar(table_body, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        self.tree.bind("<Button-3>", self._show_redeem_row_context_menu, add="+")
        self.tree.bind("<ButtonRelease-3>", self._show_redeem_row_context_menu, add="+")
        self.tree.bind("<Shift-F10>", self._show_redeem_row_context_menu, add="+")

        rail = tk.Frame(body, bg=C["card"], width=220)
        rail.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
        rail.pack_propagate(False)

        rail_hdr = tk.Frame(rail, bg=C.get("nav", C["card"]))
        rail_hdr.pack(fill=tk.X)
        tk.Label(rail_hdr, text="Actions",
                 font=("Arial", 11, "bold"),
                 bg=C.get("nav", C["card"]), fg=C["text"]).pack(side=tk.LEFT, padx=14, pady=8)

        tk.Label(rail, text="Select a code and use these actions to send, copy, import, or remove it.",
                 justify="left", wraplength=180,
                 bg=C["card"], fg=C["muted"], font=("Arial", 10)).pack(anchor="w", padx=14, pady=(16, 18))

        bb = tk.Frame(rail, bg=C["card"])
        bb.pack(fill=tk.X, padx=12)
        for txt, icon_name, clr, hclr, cmd in [
            ("Send WhatsApp", "whatsapp",    "#25d366",   "#1a9e4a", self._send_wa),
            ("Copy Code",     "save",        C["blue"],   "#154360", self._copy_code),
            ("Load File",     "import_json", C["purple"], "#6c3483", self._load_templates),
            ("Delete",        "delete",      C["red"],    "#c0392b", self._delete),
        ]:
            ModernButton(bb, text=txt, image=get_action_icon(icon_name), compound="left", command=cmd,
                         color=clr, hover_color=hclr,
                         width=180, height=38, radius=8,
                         font=("Arial", 10, "bold"),
                         ).pack(fill=tk.X, pady=5)

        self._load_list()

    def _load_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        flt   = self.filter_var.get()
        codes = get_codes()
        td    = today_str()

        for code, c in sorted(codes.items(),
                               key=lambda x: x[1].get("created",""),
                               reverse=True):
            used    = c.get("used", False)
            expired = c.get("expiry","2099-12-31") < td

            if flt == "unused"  and (used or expired): continue
            if flt == "used"    and not used:           continue
            if flt == "expired" and not (expired and not used): continue

            status = "Unused"
            if used:
                status = "Used"
            elif expired:
                status = "Expired"

            val   = safe_float(c.get("value", 0))
            dtype = c.get("discount_type","flat")
            val_s = (f"Rs{val:.0f}" if dtype == "flat"
                     else f"{val:.0f}%")

            self.tree.insert("", tk.END, values=(
                code,
                dtype.title(),
                val_s,
                c.get("phone",""),
                c.get("name",""),
                c.get("expiry",""),
                status,
            ))

    def _get_selected_code(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select","Select a code."); return None
        return self.tree.item(sel[0], "values")[0]

    def _popup_context_menu(self, event, menu, fallback_widget=None):
        x_root = getattr(event, "x_root", None)
        y_root = getattr(event, "y_root", None)
        if x_root is None or y_root is None:
            widget = fallback_widget or self
            x_root = widget.winfo_rootx() + 24
            y_root = widget.winfo_rooty() + 24
        menu.tk_popup(x_root, y_root)
        menu.grab_release()
        return "break"

    def _show_redeem_row_context_menu(self, event):
        row_id = self.tree.identify_row(getattr(event, "y", 0))
        if not row_id:
            selection = self.tree.selection()
            row_id = selection[0] if selection else self.tree.focus()
        if not row_id:
            return "break"
        try:
            self.tree.selection_set(row_id)
            values = self.tree.item(row_id, "values")
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.redeem_context_menu import get_row_sections

            selected_row = {
                "row_id": row_id,
                "code": values[0] if len(values) > 0 else "",
                "type": values[1] if len(values) > 1 else "",
                "value": values[2] if len(values) > 2 else "",
                "phone": values[3] if len(values) > 3 else "",
                "name": values[4] if len(values) > 4 else "",
                "expiry": values[5] if len(values) > 5 else "",
                "status": values[6] if len(values) > 6 else "",
            }
            context = build_context(
                "redeem_codes",
                entity_type="redeem_code",
                entity_id=selected_row["code"],
                selected_row=selected_row,
                selected_text=selected_row["code"],
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="redeem_code_tree",
                extra={"has_phone": bool(selected_row["phone"])},
            )
            menu = renderer_service.build_menu(self, get_row_sections(), context)
            return self._popup_context_menu(event, menu, self.tree)
        except Exception as exc:
            app_log(f"[redeem row context menu] {exc}")
            return "break"

    def _show_redeem_result_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.redeem_context_menu import get_result_sections

            result_text = str(self.result_lbl.cget("text") or "").strip()
            if not result_text:
                return "break"
            context = build_context(
                "redeem_codes",
                entity_type="generated_result",
                selected_text=result_text,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.CARD,
                widget_id="redeem_generated_result",
                extra={"result_text": result_text},
            )
            menu = renderer_service.build_menu(self, get_result_sections(), context)
            return self._popup_context_menu(event, menu, self.result_lbl)
        except Exception as exc:
            app_log(f"[redeem result context menu] {exc}")
            return "break"

    def _send_wa(self):
        code_str = self._get_selected_code()
        if not code_str: return

        codes = get_codes()
        c     = codes.get(code_str, {})
        phone = c.get("phone","").strip()
        name  = c.get("name","") or "Customer"

        if not phone or not validate_phone(phone):
            messagebox.showerror(
                "No Phone",
                "No phone number for this code.\n"
                "Use 'Generate for All Customers' to assign codes to customers.")
            return

        val   = safe_float(c.get("value", 0))
        dtype = c.get("discount_type","flat")
        val_s = (f"Rs{val:.0f} off" if dtype == "flat"
                 else f"{val:.0f}% off")
        exp   = c.get("expiry","")
        note  = c.get("note","")

        salon_name = get_company_name()
        msg = (f"Special Offer for {name}!\n\n"
               f"Use this code at {salon_name}:\n\n"
               f"*{code_str}*\n\n"
               f"Discount: {val_s}\n"
               f"Valid till: {exp}\n"
               + (f"Note: {note}\n" if note else "") +
               f"\nShow this code at billing to redeem.\n"
               f"- Team {salon_name}")

        # Try selenium first, fallback to pywhatkit
        self._wa_send_code(phone, msg)

    def _wa_send_code(self, phone, msg):
        """Send via selenium Ã¢â€ â€™ fallback pywhatkit."""
        import threading

        def _send():
            try:
                from whatsapp_helper import send_text
                ok = send_text(phone, msg)
                if ok:
                    self.after(0, lambda: messagebox.showinfo(
                        "Sent", f"Redeem code sent to +91{phone}!"))
                else:
                    raise Exception("send_text returned False")
            except Exception as e1:
                try:
                    import pywhatkit as kit
                    kit.sendwhatmsg_instantly(
                        f"+91{phone}", msg,
                        wait_time=25, tab_close=True, close_time=3)
                    self.after(0, lambda: messagebox.showinfo(
                        "Sent", f"Code sent via WhatsApp to +91{phone}!"))
                except Exception as e2:
                    self.after(0, lambda: messagebox.showerror(
                        "WhatsApp Error",
                        f"Could not send:\n{e2}\n\n"
                        f"Make sure WhatsApp Web is open and logged in."))

        threading.Thread(target=_send, daemon=True).start()

    def _copy_code(self):
        code = self._get_selected_code()
        if not code: return
        self.clipboard_clear()
        self.clipboard_append(code)
        messagebox.showinfo("Copied", f"Code '{code}' copied to clipboard!")

    def _copy_selected_phone(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a code.")
            return
        values = self.tree.item(sel[0], "values")
        phone = values[3] if len(values) > 3 else ""
        if not phone:
            messagebox.showwarning("No Phone", "This code does not have a phone number.")
            return
        self.clipboard_clear()
        self.clipboard_append(phone)
        messagebox.showinfo("Copied", f"Phone '{phone}' copied to clipboard!")

    def _copy_selected_name(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a code.")
            return
        values = self.tree.item(sel[0], "values")
        name = values[4] if len(values) > 4 else ""
        if not name:
            messagebox.showwarning("No Name", "This code does not have a customer name.")
            return
        self.clipboard_clear()
        self.clipboard_append(name)
        messagebox.showinfo("Copied", f"Customer '{name}' copied to clipboard!")

    def _copy_result_text(self):
        result_text = str(self.result_lbl.cget("text") or "").strip()
        if not result_text:
            return
        self.clipboard_clear()
        self.clipboard_append(result_text)
        messagebox.showinfo("Copied", "Generated result copied to clipboard.")

    def _delete(self):
        code = self._get_selected_code()
        if not code: return
        if messagebox.askyesno("Delete",
                                f"Delete code '{code}'?"):
            codes = get_codes()
            codes.pop(code, None)
            save_codes(codes)
            self._load_list()

    def _load_templates(self):
        from tkinter import filedialog
        import json
        path = filedialog.askopenfilename(
            title="Select Redeem Codes JSON",
            filetypes=[("JSON files","*.json"),("All files","*.*")])
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f:
                templates = json.load(f)
            if not isinstance(templates, dict):
                messagebox.showerror("Error","Invalid file format."); return
            existing = get_codes()
            added = 0
            for code, data in templates.items():
                if code not in existing:
                    existing[code] = data
                    added += 1
            save_codes(existing)
            self._load_list()
            messagebox.showinfo("Loaded", f"{added} new codes loaded! ({len(templates)-added} already existed)")
        except Exception as e:
            messagebox.showerror("Error", "Could not load:\n" + str(e))

    def refresh(self):
        self._load_list()

    def _register_redeem_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu_definitions.redeem_context_menu import RedeemContextAction

        action_adapter.register(RedeemContextAction.SEND_WHATSAPP, lambda _ctx, _act: self._send_wa())
        action_adapter.register(RedeemContextAction.COPY_CODE, lambda _ctx, _act: self._copy_code())
        action_adapter.register(RedeemContextAction.COPY_PHONE, lambda _ctx, _act: self._copy_selected_phone())
        action_adapter.register(RedeemContextAction.COPY_NAME, lambda _ctx, _act: self._copy_selected_name())
        action_adapter.register(RedeemContextAction.REFRESH, lambda _ctx, _act: self._load_list())
        action_adapter.register(RedeemContextAction.DELETE, lambda _ctx, _act: self._delete())
        action_adapter.register(RedeemContextAction.COPY_RESULT, lambda _ctx, _act: self._copy_result_text())

