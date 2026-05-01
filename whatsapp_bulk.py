"""
whatsapp_bulk.py  –  BOBY'S Salon : WhatsApp bulk messaging
"""
import tkinter as tk
import os
from tkinter import ttk, messagebox
import time, threading
from utils import (C, today_str, app_log)
from customers import get_customers
from ui_theme import apply_treeview_column_alignment, ModernButton
from icon_system import get_action_icon
from branding import get_invoice_branding


class WhatsAppBulkFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._register_text_context_menu_callbacks()
        self._build()

    def _build(self):
        self._build_checkbox_icons()
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        ModernButton(hdr, text="WA Login Status", image=get_action_icon("whatsapp"), compound="left",
                     command=self._check_wa_status_v51,
                     color=C["blue"], hover_color="#154360",
                     width=148, height=32, radius=8, font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT, padx=10, pady=6)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="WhatsApp Bulk Message",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Send messages to customers in bulk",
                 font=("Arial", 10), bg=C["card"], fg=C["muted"]).pack(anchor="w")
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        # Main layout
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # ── LEFT : Recipients ────────────────────
        _lf_o = tk.Frame(main, bg=C["card"])
        _lf_o.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))
        _lfh = tk.Frame(_lf_o, bg=C["sidebar"], padx=12, pady=6)
        _lfh.pack(fill=tk.X)
        tk.Label(_lfh, text="Select Recipients", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_lf_o, bg=C["teal"], height=2).pack(fill=tk.X)
        lf = tk.Frame(_lf_o, bg=C["card"], padx=12, pady=10)
        lf.pack(fill=tk.BOTH, expand=True)

        # Filter options
        self.filter_var = tk.StringVar(value="all")
        filters = [
            ("All Customers",        "all"),
            ("Birthday This Month",  "birthday_month"),
            ("Birthday Today",       "birthday_today"),
            ("Visited This Month",   "visited_month"),
            ("Not Visited (30 days)","not_visited"),
            ("High Loyalty Points",  "high_points"),
        ]
        for txt, val in filters:
            tk.Radiobutton(lf, text=txt,
                           variable=self.filter_var, value=val,
                           bg=C["card"], fg=C["text"],
                           selectcolor=C["input"],
                           font=("Arial", 11),
                           cursor="hand2",
                           command=self._apply_filter).pack(
                               anchor="w", pady=1)

        ModernButton(lf, text="Apply Filter", image=get_action_icon("filter"), compound="left",
                     command=self._apply_filter,
                     color=C["teal"], hover_color=C["blue"],
                     width=200, height=32, radius=8, font=("Arial",10,"bold"),
                     ).pack(fill=tk.X, pady=(8,4))

        # Customer list
        self.count_lbl = tk.Label(lf, text="Recipients: 0",
                                   bg=C["card"], fg=C["lime"],
                                   font=("Arial", 12, "bold"))
        self.count_lbl.pack(anchor="w", pady=(4, 4))

        cols = ("Name", "Phone")
        self.tree = ttk.Treeview(lf, columns=cols,
                                  show="tree headings", height=14)
        self.tree.heading("#0", text="")
        self.tree.heading("Name",  text="Name")
        self.tree.heading("Phone", text="Phone")
        self.tree.column("#0", width=42, anchor="center", stretch=False)
        self.tree.column("Name",  width=160)
        self.tree.column("Phone", width=110)
        apply_treeview_column_alignment(self.tree)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Button-1>", self._toggle_check)

        sel_row = tk.Frame(lf, bg=C["card"])
        sel_row.pack(fill=tk.X, pady=(6, 0))
        ModernButton(sel_row, text="Select All", image=get_action_icon("add"), compound="left",
                     command=lambda: self._sel_all(True),
                     color=C["teal"], hover_color=C["blue"],
                     width=100, height=28, radius=8, font=("Arial",9,"bold"),
                     ).pack(side=tk.LEFT, padx=(0,4))
        ModernButton(sel_row, text="Deselect All", image=get_action_icon("clear"), compound="left",
                     command=lambda: self._sel_all(False),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=110, height=28, radius=8, font=("Arial",9,"bold"),
                     ).pack(side=tk.LEFT)

        # ── RIGHT : Message ──────────────────────
        rf = tk.Frame(main, bg=C["bg"])
        rf.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Templates
        _tf_o = tk.Frame(rf, bg=C["card"])
        _tf_o.pack(fill=tk.X, pady=(0,8))
        _tfh = tk.Frame(_tf_o, bg=C["sidebar"], padx=12, pady=6)
        _tfh.pack(fill=tk.X)
        tk.Label(_tfh, text="Message Templates", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_tf_o, bg=C["purple"], height=2).pack(fill=tk.X)
        tf = tk.Frame(_tf_o, bg=C["card"], padx=12, pady=10)
        tf.pack(fill=tk.X)

        templates = {
            "🎉 Offer / Discount": (
                "🌟 Special Offer from {salon_name}! 🌟\n\n"
                "Dear {name},\n\n"
                "We have an exclusive offer just for you! 💅\n"
                "✨ Get 20% off on all services this week!\n\n"
                "Book your appointment now.\n"
                "📞 Call us: {salon_phone}\n\n"
                "— Team {salon_name}"
            ),
            "🎂 Birthday Wishes": (
                "🎂 Happy Birthday {name}! 🎉\n\n"
                "Wishing you a beautiful and joyful day! 💐\n\n"
                "Visit {salon_name} for a special birthday treat! ✨\n\n"
                "📞 {salon_phone}\n\n"
                "— Team {salon_name}"
            ),
            "💆 Service Reminder": (
                "Hi {name}! 👋\n\n"
                "It's been a while since your last visit to {salon_name}.\n\n"
                "We miss you! Come back for a relaxing session. 💅✨\n\n"
                "Book your appointment today!\n"
                "📞 {salon_phone}\n\n"
                "— Team {salon_name}"
            ),
            "🎊 Festival Greetings": (
                "🎊 Season's Greetings from {salon_name}! 🎊\n\n"
                "Dear {name},\n\n"
                "Wishing you and your family joy, health, and happiness! 🌸\n\n"
                "📞 {salon_phone}\n\n"
                "— Team {salon_name}"
            ),
        }
        self._templates = templates

        t_row = tk.Frame(tf, bg=C["card"])
        t_row.pack(fill=tk.X)
        tk.Label(t_row, text="Template:", bg=C["card"],
                 fg=C["muted"], font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 6))
        self.tmpl_var = tk.StringVar(value=list(templates.keys())[0])
        ttk.Combobox(t_row, textvariable=self.tmpl_var,
                     values=list(templates.keys()),
                     state="readonly",
                     font=("Arial", 12),
                     width=30).pack(side=tk.LEFT, padx=(0, 8))
        ModernButton(t_row, text="Load", image=get_action_icon("search"), compound="left",
                     command=self._load_template,
                     color=C["blue"], hover_color="#154360",
                     width=80, height=30, radius=8, font=("Arial",10,"bold"),
                     ).pack(side=tk.LEFT)

        # Message box
        _mf2_o = tk.Frame(rf, bg=C["card"])
        _mf2_o.pack(fill=tk.BOTH, expand=True, pady=(0,8))
        _mf2h = tk.Frame(_mf2_o, bg=C["sidebar"], padx=12, pady=6)
        _mf2h.pack(fill=tk.X)
        tk.Label(_mf2h, text="Message ({name} = customer name)",
                 font=("Arial",11,"bold"), bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_mf2_o, bg=C["accent"], height=2).pack(fill=tk.X)
        mf2 = tk.Frame(_mf2_o, bg=C["card"], padx=12, pady=10)
        mf2.pack(fill=tk.BOTH, expand=True)

        self.msg_txt = tk.Text(mf2, font=("Arial", 12),
                                bg=C["input"], fg=C["text"],
                                bd=0, insertbackground=C["accent"],
                                wrap="word", height=14)
        self.msg_txt.pack(fill=tk.BOTH, expand=True)
        self.msg_txt.bind("<Button-3>", lambda event: self._show_text_context_menu(event, self.msg_txt, "whatsapp_message"), add="+")
        self.msg_txt.bind("<Shift-F10>", lambda event: self._show_text_context_menu(event, self.msg_txt, "whatsapp_message"), add="+")
        self._load_template()

        # Image attachment
        _img_o = tk.Frame(rf, bg=C["card"])
        _img_o.pack(fill=tk.X, pady=(0,8))
        _imgh = tk.Frame(_img_o, bg=C["sidebar"], padx=12, pady=6)
        _imgh.pack(fill=tk.X)
        tk.Label(_imgh, text="Attach Image (optional)", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_img_o, bg=C["blue"], height=2).pack(fill=tk.X)
        img_f = tk.Frame(_img_o, bg=C["card"], padx=12, pady=8)
        img_f.pack(fill=tk.X)

        img_row = tk.Frame(img_f, bg=C["card"])
        img_row.pack(fill=tk.X)

        self.img_path_var = tk.StringVar(value="")
        self.img_path_lbl = tk.Label(img_row,
                                      text="No image selected",
                                      bg=C["card"], fg=C["muted"],
                                      font=("Arial", 11), anchor="w")
        self.img_path_lbl.pack(side=tk.LEFT, fill=tk.X,
                                expand=True)
        self.img_path_lbl.bind("<Button-3>", self._show_image_path_context_menu, add="+")
        self.img_path_lbl.bind("<Shift-F10>", self._show_image_path_context_menu, add="+")

        ModernButton(img_row, text="Browse Image", image=get_action_icon("browse"), compound="left",
                     command=self._pick_image,
                     color=C["blue"], hover_color="#154360",
                     width=130, height=30, radius=8, font=("Arial",10,"bold"),
                     ).pack(side=tk.RIGHT)

        ModernButton(img_f, text="Remove Image", image=get_action_icon("clear"), compound="left",
                     command=lambda: (self.img_path_var.set(""),
                                      self.img_path_lbl.config(
                                          text="No image selected",
                                          fg=C["muted"])),
                     color=C["sidebar"], hover_color="#c0392b",
                     width=130, height=28, radius=8, font=("Arial",9,"bold"),
                     ).pack(anchor="w", pady=(4,0))

        tk.Label(img_f,
                 text="Image will be sent along with the message to each customer.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 10)).pack(anchor="w")

        # Send controls
        sf = tk.Frame(rf, bg=C["bg"])
        sf.pack(fill=tk.X)

        tk.Label(sf, text="Delay (secs between msgs):",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 5))
        self.delay_var = tk.StringVar(value="20")
        self.delay_ent = tk.Entry(sf, textvariable=self.delay_var,
                                  font=("Arial", 12), bg=C["input"],
                                  fg=C["text"], bd=0, width=6,
                                  insertbackground=C["accent"])
        self.delay_ent.pack(side=tk.LEFT, ipady=4, padx=(0, 10))
        self.delay_ent.bind("<Button-3>", lambda event: self._show_text_context_menu(event, self.delay_ent, "whatsapp_delay"), add="+")
        self.delay_ent.bind("<Shift-F10>", lambda event: self._show_text_context_menu(event, self.delay_ent, "whatsapp_delay"), add="+")

        self.send_btn = ModernButton(sf, text="SEND TO ALL SELECTED", image=get_action_icon("whatsapp"), compound="left",
                                     command=self._confirm_send,
                                     color="#25d366", hover_color="#1a9e4a",
                                     width=300, height=38, radius=8, font=("Arial",11,"bold"))
        self.send_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Progress
        self.progress_lbl = tk.Label(rf, text="",
                                      bg=C["bg"], fg=C["lime"],
                                      font=("Arial", 12))
        self.progress_lbl.pack(anchor="w", pady=(4, 0))

        self._checked = {}
        self._apply_filter()

    def _build_checkbox_icons(self):
        self._checkbox_off = tk.PhotoImage(width=16, height=16)
        self._checkbox_off.put(C["card"], to=(0, 0, 16, 16))
        self._checkbox_off.put("#6b778d", to=(1, 1, 15, 2))
        self._checkbox_off.put("#6b778d", to=(1, 14, 15, 15))
        self._checkbox_off.put("#6b778d", to=(1, 1, 2, 15))
        self._checkbox_off.put("#6b778d", to=(14, 1, 15, 15))
        self._checkbox_off.put("#ffffff", to=(2, 2, 14, 14))

        self._checkbox_on = tk.PhotoImage(width=16, height=16)
        self._checkbox_on.put(C["card"], to=(0, 0, 16, 16))
        self._checkbox_on.put("#1677ff", to=(1, 1, 15, 15))
        tick_pixels = [
            (4, 8), (5, 9), (6, 10),
            (7, 9), (8, 8), (9, 7),
            (10, 6), (11, 5),
            (4, 9), (5, 10), (6, 11),
            (7, 10), (8, 9), (9, 8),
            (10, 7), (11, 6),
        ]
        for x, y in tick_pixels:
            self._checkbox_on.put("#ffffff", to=(x, y, x + 1, y + 1))

    def _pick_image(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select Offer Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
                ("All files",   "*.*"),
            ])
        if path:
            self.img_path_var.set(path)
            fname = path.split("/")[-1].split("\\")[-1]
            self.img_path_lbl.config(
                text=f"Selected: {fname}", fg=C["lime"])

    def _load_template(self):
        tmpl = self._templates.get(self.tmpl_var.get(), "")
        # Replace salon placeholders from settings
        try:
            from salon_settings import get_settings
            cfg         = get_settings()
            salon_name  = cfg.get("salon_name", get_invoice_branding().get("salon_name", "B-Lite Management"))
            salon_phone = cfg.get("phone", "") or "—"
        except Exception:
            salon_name  = get_invoice_branding().get("salon_name", "B-Lite Management")
            salon_phone = "—"
        tmpl = tmpl.replace("{salon_name}",  salon_name)
        tmpl = tmpl.replace("{salon_phone}", salon_phone)
        self.msg_txt.delete("1.0", tk.END)
        self.msg_txt.insert("1.0", tmpl)

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

    def _show_text_context_menu(self, event, widget, widget_id: str):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.global_text_context_menu import get_sections

            selected_text = ""
            try:
                selected_text = str(widget.selection_get())
            except Exception:
                selected_text = ""

            widget_type = WidgetType.TEXT if isinstance(widget, tk.Text) else WidgetType.ENTRY
            context = build_context(
                "whatsapp_bulk",
                entity_type="message_text",
                selected_text=selected_text,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=widget_type,
                widget_id=widget_id,
                extra={"widget": widget},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            return self._popup_context_menu(event, menu, widget)
        except Exception as exc:
            app_log(f"[whatsapp text context menu] {exc}")
            return "break"

    def _show_image_path_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy image path", command=self._copy_image_path)
        return self._popup_context_menu(event, menu, self.img_path_lbl)

    def _copy_image_path(self):
        image_path = self.img_path_var.get().strip()
        if not image_path:
            return
        self.clipboard_clear()
        self.clipboard_append(image_path)
        self.progress_lbl.config(text="Image path copied.")

    def _apply_filter(self):
        flt       = self.filter_var.get()
        customers = get_customers()
        today     = today_str()
        today_md  = today[-5:]  # MM-DD
        month_mo  = today[:7]

        filtered = []
        for ph, c in customers.items():
            if not ph or ph == "0000000000": continue

            visits   = c.get("visits", [])
            last_v   = visits[-1]["date"][:10] if visits else ""
            birthday = c.get("birthday","")
            pts      = c.get("points", 0)

            if flt == "all":
                pass
            elif flt == "birthday_today":
                if not birthday.endswith(today_md): continue
            elif flt == "birthday_month":
                if not birthday[5:7] == today[5:7]: continue
            elif flt == "visited_month":
                if not any(v["date"][:7] == month_mo for v in visits): continue
            elif flt == "not_visited":
                from datetime import date, timedelta
                cutoff = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
                if last_v >= cutoff: continue
            elif flt == "high_points":
                if pts < 50: continue

            filtered.append((ph, c.get("name", ""), pts))

        for i in self.tree.get_children():
            self.tree.delete(i)
        self._checked = {}

        for ph, name, pts in sorted(filtered, key=lambda x: x[1]):
            iid = self.tree.insert("", tk.END,
                                    text="",
                                    image=self._checkbox_off,
                                    values=(name, ph))
            self._checked[iid] = False

        self._update_count()

    def _toggle_check(self, e):
        region = self.tree.identify("region", e.x, e.y)
        if region not in {"tree", "cell"}:
            return
        col = self.tree.identify_column(e.x)
        if col != "#0":
            return
        iid = self.tree.identify_row(e.y)
        if not iid: return
        self._checked[iid] = not self._checked.get(iid, False)
        self.tree.item(
            iid,
            image=self._checkbox_on if self._checked[iid] else self._checkbox_off,
        )
        self._update_count()

    def _sel_all(self, state: bool):
        for iid in self.tree.get_children():
            self._checked[iid] = state
            self.tree.item(
                iid,
                image=self._checkbox_on if state else self._checkbox_off,
            )
        self._update_count()

    def _update_count(self):
        n = sum(1 for v in self._checked.values() if v)
        self.count_lbl.config(text=f"Recipients: {n}")

    def _confirm_send(self):
        selected = [(self.tree.item(iid, "values")[0],
                     self.tree.item(iid, "values")[1])
                    for iid, checked in self._checked.items() if checked]
        if not selected:
            messagebox.showwarning("No Recipients",
                                    "Select at least one recipient."); return
        msg = self.msg_txt.get("1.0", tk.END).strip()
        if not msg:
            messagebox.showwarning("No Message", "Write a message."); return

        confirm = messagebox.askyesno(
            "Confirm Send",
            f"Send WhatsApp message to {len(selected)} customers?\n\n"
            f"WhatsApp Web must be logged in.\n"
            f"Do NOT close the browser during sending.")
        if confirm:
            self.send_btn._lbl.config(state="disabled")
            img = self.img_path_var.get().strip()
            t = threading.Thread(target=self._send_thread,
                                  args=(selected, msg, img),
                                  daemon=True)
            t.start()

    def _send_thread(self, recipients, msg_template, img_path=""):
        from whatsapp_helper import bulk_send

        delay = max(8, int(self.delay_var.get() or "15"))

        def _progress(cur, total, name):
            self.after(0, lambda: self.progress_lbl.config(
                text=f"Sending {cur}/{total}: {name}..."))

        def _done(sent, fail, err=""):
            if err:
                err_msg = (f"Could not send:\n{err}\n\n"
                           "Make sure:\n"
                           "1. Chrome is installed\n"
                           "2. Run: pip install selenium webdriver-manager\n"
                           "3. WhatsApp Web is logged in")
                self.after(0, lambda: messagebox.showerror(
                    "WhatsApp Error", err_msg))
            else:
                self.after(0, lambda: self.progress_lbl.config(
                    text=f"Done. Sent: {sent}  Failed: {fail}"))
            self.after(0, lambda: self.send_btn._lbl.config(state="normal"))

        bulk_send(
            recipients=recipients,
            message_template=msg_template,
            image_path=img_path,
            delay=delay,
            progress_cb=_progress,
            done_cb=_done,
        )

    def _check_wa_status(self):
        import threading
        self.progress_lbl.config(
            text="Checking WhatsApp Web status...")
        def _check():
            try:
                from whatsapp_helper import check_login_status, open_whatsapp_web
                status = check_login_status(timeout=15)
                if status == "logged_in":
                    self.after(0, lambda: self.progress_lbl.config(
                        text="✅  WhatsApp Web: Logged In — Ready to send!"))
                elif status == "logged_out":
                    self.after(0, lambda: (
                        self.progress_lbl.config(
                            text="⚠️  WhatsApp Web: Not logged in — Scan QR code in Chrome"),
                        open_whatsapp_web()))
                else:
                    self.after(0, lambda: self.progress_lbl.config(
                        text=f"⚠️  Status: {status} — Open WhatsApp Web manually"))
            except Exception as e:
                err_txt = f"❌ Error: {e}\npip install selenium webdriver-manager"
                self.after(0, lambda: self.progress_lbl.config(
                    text=err_txt))
        threading.Thread(target=_check, daemon=True).start()

    def _check_wa_status_v51(self):
        import threading
        self.progress_lbl.config(text="Checking WhatsApp Web status...")

        def _check():
            try:
                from whatsapp_helper import ensure_session_ready
                snapshot = ensure_session_ready(wait_for_login=15)
                state = snapshot.get("state")
                if state == "READY":
                    self.after(0, lambda: self.progress_lbl.config(
                        text="WhatsApp Web ready to send."))
                elif state == "WAITING_FOR_LOGIN":
                    self.after(0, lambda: self.progress_lbl.config(
                        text="WhatsApp opened. Scan QR and keep the tab open."))
                else:
                    self.after(0, lambda: self.progress_lbl.config(
                        text=snapshot.get("message", f"Status: {state}")))
            except Exception as e:
                self.after(0, lambda: self.progress_lbl.config(
                    text=f"Error: {e}"))

        threading.Thread(target=_check, daemon=True).start()

    def refresh(self):
        self._apply_filter()

    def _dispatch_text_action(self, ctx, action_id: str):
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu.constants import CommonActionId

        widget = ctx.extra.get("widget")
        if widget is None:
            return False
        if action_id == CommonActionId.COPY:
            return clipboard_service.copy_selection(widget)
        if action_id == CommonActionId.PASTE:
            return clipboard_service.paste_text(widget)
        if action_id == CommonActionId.CUT:
            return clipboard_service.cut_selection(widget)
        if action_id == CommonActionId.SELECT_ALL:
            return clipboard_service.select_all(widget)
        if action_id == CommonActionId.COPY_ALL:
            return clipboard_service.copy_all(widget)
        return False

    def _register_text_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.constants import CommonActionId

        action_adapter.register(CommonActionId.COPY, lambda ctx, _act: self._dispatch_text_action(ctx, CommonActionId.COPY))
        action_adapter.register(CommonActionId.PASTE, lambda ctx, _act: self._dispatch_text_action(ctx, CommonActionId.PASTE))
        action_adapter.register(CommonActionId.CUT, lambda ctx, _act: self._dispatch_text_action(ctx, CommonActionId.CUT))
        action_adapter.register(CommonActionId.SELECT_ALL, lambda ctx, _act: self._dispatch_text_action(ctx, CommonActionId.SELECT_ALL))
        action_adapter.register(CommonActionId.COPY_ALL, lambda ctx, _act: self._dispatch_text_action(ctx, CommonActionId.COPY_ALL))


