"""
staff.py – BOBY'S Salon : Staff management + commission tracking
FIXES:
  - Bug 14: removed unused CSV read in _calc_commission (wasted I/O)
  - Bug 15: _mark_att() no longer sets out_time on Absent/Leave
  - Fix R2a: _load_tree() try/except — crash prevention
  - Fix R2b: _staff_form save block try/except — error shown to user
  - Fix R2c: _toggle_active() try/except — error shown to user
  - Fix R2d: _delete() try/except — error shown to user
  - Fix R2e: _load_attendance() try/except — crash prevention
  - Fix R2f: _mark_att() save block try/except — error shown to user
  - Fix R2g: _clock_out() save block try/except — error shown to user
  - Fix R2h: _calc_commission() try/except — crash prevention
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from utils import (C, load_json, save_json, safe_float,
                   F_STAFF, fmt_currency, now_str, today_str, month_str,
                   popup_window, app_log, DATA_DIR,
                   attendance_get_day_record,
                   attendance_get_sessions,
                   attendance_sync_legacy_fields,
                   attendance_latest_session,
                   attendance_open_session)
import os
from tkinter import filedialog
from ui_theme import apply_treeview_column_alignment, ModernButton
from ui_responsive import make_scrollable
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready


class StaffFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _is_owner_user(self) -> bool:
        return str(getattr(self.app, "current_user", {}).get("role", "staff")).strip().lower() == "owner"

    def _format_session_duration(self, in_time: str, out_time: str) -> str:
        if not in_time or not out_time:
            return "-"
        try:
            start = datetime.strptime(in_time, "%H:%M")
            end = datetime.strptime(out_time, "%H:%M")
            mins = int((end - start).total_seconds() // 60)
            if mins < 0:
                mins = 0
            hrs, rem = divmod(mins, 60)
            return f"{hrs}h {rem}m" if hrs else f"{rem}m"
        except Exception:
            return "-"

    def _refresh_session_history(self, *_args):
        if not getattr(self, "_show_session_history", False):
            return
        if not hasattr(self, "session_tree"):
            return
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        sel = self.att_tree.selection() if hasattr(self, "att_tree") else ()
        if not sel:
            self._session_meta_var.set("Select a staff row to view today's login and logout sessions.")
            return
        values = self.att_tree.item(sel[0], "values")
        if not values:
            self._session_meta_var.set("Select a staff row to view today's login and logout sessions.")
            return
        staff_name = values[0]
        dt = self.att_date.get().strip() if hasattr(self, "att_date") else today_str()
        staff = get_staff()
        rec = attendance_get_day_record(staff.get(staff_name, {}).get("attendance", []), dt)
        if rec:
            rec = attendance_sync_legacy_fields(rec)
        sessions = attendance_get_sessions(rec) if rec else []
        self._session_meta_var.set(f"{staff_name}  |  {dt}  |  {len(sessions)} session(s)")
        if not sessions:
            self.session_tree.insert("", tk.END, values=("-", "-", "-", "No sessions"))
            return
        for idx, sess in enumerate(sessions, start=1):
            in_t = str(sess.get("in_time", "") or "-")
            out_t = str(sess.get("out_time", "") or "-")
            dur = self._format_session_duration("" if in_t == "-" else in_t, "" if out_t == "-" else out_t)
            self.session_tree.insert("", tk.END, values=(idx, in_t, out_t, dur))

    def _build(self):
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left_f = tk.Frame(hdr, bg=C["card"])
        left_f.pack(side=tk.LEFT, padx=20)
        tk.Label(left_f, text="👩‍💼  Staff Management",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left_f, text="Manage staff, attendance & commissions",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")
        ModernButton(hdr, text="➕  Add Staff",
                     command=self._add_dialog,
                     color=C["teal"], hover_color=C["blue"],
                     width=130, height=34, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.RIGHT, padx=15, pady=6)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        top_band = tk.Frame(self, bg=C["bg"])
        top_band.pack(fill=tk.X, padx=15, pady=(8, 6))
        intro = tk.Frame(top_band, bg=C["card"], padx=18, pady=12)
        intro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(intro, text="Staff Workspace",
                 bg=C["card"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(intro, text="Manage employees, review attendance, and track commission from one focused screen.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 10)).pack(anchor="w", pady=(4, 0))

        self._staff_summary_band = tk.Frame(top_band, bg=C["bg"])
        self._staff_summary_band.pack(side=tk.RIGHT, padx=(10, 0))
        self._staff_summary_cards = {}
        for key, title, color in [
            ("total", "Team", C["blue"]),
            ("active", "Active", C["green"]),
            ("managers", "Leads", C["accent"]),
        ]:
            card = tk.Frame(self._staff_summary_band, bg=C["card"], padx=14, pady=10)
            card.pack(side=tk.LEFT, padx=(0, 8))
            value_lbl = tk.Label(card, text="0",
                                 bg=C["card"], fg=color,
                                 font=("Arial", 14, "bold"))
            value_lbl.pack(anchor="w")
            tk.Label(card, text=title, bg=C["card"], fg=C["muted"],
                     font=("Arial", 10)).pack(anchor="w")
            tk.Frame(card, bg=color, height=2).pack(fill=tk.X, pady=(8, 0))
            self._staff_summary_cards[key] = value_lbl

        # —€—€ Tab row: notebook tabs LEFT + action buttons RIGHT —€—€
        tab_bar = tk.Frame(self, bg=C["bg"])
        tab_bar.pack(fill=tk.X, padx=15, pady=(6, 0))

        # Action buttons — RIGHT side of tab bar
        self._staff_btn_frame = tk.Frame(tab_bar, bg=C["bg"])
        self._staff_btn_frame.pack(side=tk.RIGHT)
        self._edit_btn = ModernButton(
            self._staff_btn_frame, text="Edit", command=self._edit_dialog,
            color=C["blue"], hover_color="#154360",
            width=118, height=32, radius=8, font=("Arial", 10, "bold"),
        )
        self._edit_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._toggle_btn = ModernButton(
            self._staff_btn_frame, text="Toggle Active", command=self._toggle_active,
            color=C["orange"], hover_color="#d35400",
            width=152, height=32, radius=8, font=("Arial", 10, "bold"),
        )
        self._toggle_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._delete_btn = ModernButton(
            self._staff_btn_frame, text="Delete", command=self._delete,
            color=C["red"], hover_color="#c0392b",
            width=118, height=32, radius=8, font=("Arial", 10, "bold"),
        )
        self._delete_btn.pack(side=tk.LEFT, padx=(0, 4))
        if False:
            ("✏️  Edit",          C["blue"],   "#154360",  self._edit_dialog),
            ("🚫  Toggle Active", C["orange"], "#d35400",  self._toggle_active),
            ("🗑️  Delete",        C["red"],    "#c0392b",  self._delete),
            pass
            ModernButton(self._staff_btn_frame, text=txt, command=cmd,
                         color=clr, hover_color=hclr,
                         width=138, height=32, radius=8,
                         font=("Arial", 10, "bold"),
                         ).pack(side=tk.LEFT, padx=(0, 4))

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(4, 10))

        t1 = tk.Frame(nb, bg=C["bg"])
        t2 = tk.Frame(nb, bg=C["bg"])
        t3 = tk.Frame(nb, bg=C["bg"])

        nb.add(t1, text="👥  Staff List")
        nb.add(t2, text="🕐  Attendance")
        nb.add(t3, text="💰  Commission")

        # Hide buttons when not on Staff List tab
        def _on_tab_change(e):
            idx = nb.index(nb.select())
            if idx == 0:
                self._staff_btn_frame.pack(side=tk.RIGHT)
            else:
                self._staff_btn_frame.pack_forget()
        nb.bind("<<NotebookTabChanged>>", _on_tab_change)

        self._build_staff_list(t1)
        self._build_attendance(t2)
        self._build_commission(t3)

    def _rbac_denied(self) -> bool:
        if self.app.has_permission("manage_staff"):
            return False
        messagebox.showerror("Access Denied",
                             "Staff management is restricted for your role.")
        return True

    # —€—€ Staff List —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    def _build_staff_list(self, parent):
        # —€—€ Split: left=tree+buttons, divider, right=stats —€—€
        split = tk.Frame(parent, bg=C["bg"])
        split.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 6))

        # Stats panel — RIGHT side, fixed width 220px default
        try:
            _sw = split.winfo_screenwidth()
        except Exception:
            _sw = 1366
        _stats_default_w = int(_sw * 0.22) if _sw < 1366 else int(_sw * 0.28)
        _stats_default_w = max(180, _stats_default_w)
        self._stats_panel = tk.Frame(split, bg=C["card"], width=_stats_default_w)
        self._stats_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self._stats_panel.pack_propagate(False)

        # —€—€ Drag divider — between tree and stats —€—€—€—€—€—€—€—€—€
        self._divider = tk.Frame(split, bg=C["sidebar"], width=6,
                                  cursor="sb_h_double_arrow")
        self._divider.pack(side=tk.RIGHT, fill=tk.Y)

        # AnimationEngine smooth_drag — debounced, visual feedback
        try:
            _dsw = split.winfo_screenwidth()
        except Exception:
            _dsw = 1366
        from ui_theme import anim
        anim.smooth_drag(self._divider, self._stats_panel,
                         min_w=max(160, int(_dsw * 0.12)),
                         max_w=int(_dsw * 0.55),
                         debounce=1)

        # Tree side — LEFT, fills remaining space —€—€—€—€—€—€—€—€—€—€
        tree_f = tk.Frame(split, bg=C["bg"])
        tree_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_bar = tk.Frame(tree_f, bg=C["card"], padx=12, pady=10)
        search_bar.pack(fill=tk.X, pady=(0, 8))
        tk.Label(search_bar, text="Staff Directory",
                 bg=C["card"], fg=C["text"],
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(search_bar, text="Search by name, role, or phone",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 9)).pack(side=tk.RIGHT)

        search_row = tk.Frame(tree_f, bg=C["bg"])
        search_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(search_row, text="Search:", bg=C["bg"], fg=C["muted"],
                 font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self._staff_search_var = tk.StringVar()
        search_entry = tk.Entry(search_row, textvariable=self._staff_search_var,
                                font=("Arial", 11), bg=C["input"], fg=C["text"],
                                bd=0, insertbackground=C["accent"])
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self._staff_search_var.trace_add("write", lambda *_: self._load_tree())
        ModernButton(search_row, text="Clear",
                     command=lambda: self._staff_search_var.set(""),
                     color=C["sidebar"], hover_color=C["blue"],
                     width=84, height=30, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(8, 0))

        # Phase 5.6.1 Phase 2: visible search result count label
        self._staff_result_label = tk.Label(search_row, text="",
                                            bg=C["bg"], fg=C["muted"],
                                            font=("Arial", 10))
        self._staff_result_label.pack(side=tk.LEFT, padx=(10, 0))

        # —€—€ Treeview —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
        cols = ("Name", "Role", "Phone", "Commission %", "Active")
        self.tree = ttk.Treeview(tree_f, columns=cols,
                                 show="headings")
        for col, w in zip(cols, [170, 120, 130, 110, 70]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)
        apply_treeview_column_alignment(self.tree)
        self.tree.tag_configure("inactive", foreground=C["muted"])
        self.tree.tag_configure("active", foreground=C["text"])
        vsb = ttk.Scrollbar(tree_f, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Header
        sp_hdr = tk.Frame(self._stats_panel, bg=C["sidebar"], padx=10, pady=8)
        sp_hdr.pack(fill=tk.X)
        tk.Label(sp_hdr, text="📊  Staff Overview",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(anchor="w")
        tk.Frame(self._stats_panel, bg=C["teal"], height=2).pack(fill=tk.X)

        # Placeholder
        self._stats_body = tk.Frame(self._stats_panel, bg=C["card"], padx=12, pady=10)
        self._stats_body.pack(fill=tk.BOTH, expand=True)
        tk.Label(self._stats_body,
                 text="Select a staff member\nto view details",
                 font=("Arial", 11), bg=C["card"],
                 fg=C["muted"], justify="center").pack(expand=True)

        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self._on_staff_select)
        self.tree.bind("<Button-3>", self._show_staff_context_menu)
        self._load_tree()

    def _on_staff_select(self, e=None):
        """Show selected staff stats in the right panel."""
        try:
            sel = self.tree.selection()
            if not sel:
                return
            name = self.tree.item(sel[0], "values")[0]
            self._show_staff_stats(name)
            staff = get_staff()
            s = staff.get(name, {})
            if not s:
                s = next((sv for sk, sv in staff.items()
                          if str(sk).strip().casefold() == str(name).strip().casefold()), {})
            is_active = not bool(s.get("inactive", False))
            if hasattr(self, "_toggle_btn"):
                self._toggle_btn.set_text("Deactivate" if is_active else "Activate")
                self._toggle_btn.set_color(
                    C["orange"] if is_active else C["green"],
                    "#d35400" if is_active else C["teal"],
                )
        except Exception as ex:
            app_log(f"[_on_staff_select] {ex}")

    def _show_staff_stats(self, name: str):
        """Populate stats panel with selected staff details."""
        try:
            for w in self._stats_body.winfo_children():
                w.destroy()

            staff = get_staff()
            s = staff.get(name, {})
            if not s:
                return

            mo = month_str()
            td = today_str()

            # Attendance this month
            att_list   = s.get("attendance", [])
            mo_att     = [a for a in att_list if a.get("date", "")[:7] == mo]
            present    = sum(1 for a in mo_att if a.get("status") == "Present")
            absent     = sum(1 for a in mo_att if a.get("status") == "Absent")
            leave      = sum(1 for a in mo_att if a.get("status") == "Leave")
            total_days = len(mo_att)
            att_pct    = int(present / total_days * 100) if total_days else 0
            mo_att     = [attendance_sync_legacy_fields(a)
                          for a in att_list if a.get("date", "")[:7] == mo]
            present    = sum(1 for a in mo_att if a.get("status") == "Present")
            absent     = sum(1 for a in mo_att if a.get("status") == "Absent")
            leave      = sum(1 for a in mo_att if a.get("status") == "Leave")
            total_days = len(mo_att)
            att_pct    = int(present / total_days * 100) if total_days else 0

            # Today's attendance
            today_att  = next((a for a in att_list if a.get("date") == td), None)
            today_status = today_att.get("status", "—") if today_att else "—"
            today_in     = today_att.get("in_time", "—") if today_att else "—"
            today_out    = today_att.get("out_time", "—") if today_att else "—"
            today_att    = attendance_get_day_record(att_list, td)
            latest_sess  = None
            if today_att:
                today_att = attendance_sync_legacy_fields(today_att)
                latest_sess = attendance_latest_session(today_att)
            today_status = today_att.get("status", "—") if today_att else "—"
            today_in     = (latest_sess.get("in_time", "") if latest_sess else
                            (today_att.get("in_time", "—") if today_att else "—"))
            today_out    = (latest_sess.get("out_time", "") if latest_sess else
                            (today_att.get("out_time", "—") if today_att else "—"))
            if not today_in:
                today_in = "—"
            if not today_out:
                today_out = "—"

            # Sales this month
            mo_sales = sum(
                safe_float(sale.get("amount", 0))
                for sale in s.get("sales", [])
                if sale.get("month", "") == mo
            )
            comm_pct  = safe_float(s.get("commission_pct", 0))
            comm_earn = mo_sales * comm_pct / 100

            # Status color
            status_colors = {
                "Present": C["green"], "Absent": C["red"],
                "Leave": C["orange"], "—": C["muted"]
            }

            # —€—€ Photo + Name + Role —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
            name_f = tk.Frame(self._stats_body, bg=C["card"])
            name_f.pack(fill=tk.X, pady=(0, 8))

            # Photo area (60Ã—60)
            photo_path = s.get("photo_path", "")
            photo_shown = False
            if photo_path and os.path.exists(photo_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(photo_path).convert("RGBA")
                    img = img.resize((60, 60))
                    self._staff_photo_img = ImageTk.PhotoImage(img)
                    photo_lbl = tk.Label(name_f,
                                         image=self._staff_photo_img,
                                         bg=C["card"], cursor="hand2")
                    photo_lbl.pack(side=tk.LEFT)
                    photo_lbl.bind("<Button-1>",
                        lambda e, n=name: self._change_photo(n))
                    photo_shown = True
                except Exception:
                    pass

            if not photo_shown:
                # Avatar circle fallback — click to add photo
                avatar_f = tk.Frame(name_f, bg=C["teal"],
                                     width=60, height=60, cursor="hand2")
                avatar_f.pack(side=tk.LEFT)
                avatar_f.pack_propagate(False)
                av_lbl = tk.Label(avatar_f, text=name[0].upper(),
                                   font=("Arial", 22, "bold"),
                                   bg=C["teal"], fg="white",
                                   cursor="hand2")
                av_lbl.pack(expand=True)
                for w in (avatar_f, av_lbl):
                    w.bind("<Button-1>",
                        lambda e, n=name: self._change_photo(n))
                # Hint label
                tk.Label(name_f, text="📷",
                          font=("Arial", 9),
                          bg=C["card"], fg=C["muted"],
                          cursor="hand2").place(
                              in_=avatar_f, relx=0.65, rely=0.65)

            name_info = tk.Frame(name_f, bg=C["card"])
            name_info.pack(side=tk.LEFT, padx=(10, 0))
            tk.Label(name_info, text=name,
                     font=("Arial", 12, "bold"),
                     bg=C["card"], fg=C["text"]).pack(anchor="w")
            tk.Label(name_info, text=s.get("role", ""),
                     font=("Arial", 10),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")
            tk.Label(name_info, text=s.get("phone", ""),
                     font=("Arial", 10),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")
            # Add/change photo button
            ModernButton(name_info, text="📷 Photo",
                         command=lambda n=name: self._change_photo(n),
                         color=C["sidebar"], hover_color=C["blue"],
                         width=80, height=24, radius=6,
                         font=("Arial", 9, "bold"),
                         ).pack(anchor="w", pady=(4, 0))

            tk.Frame(self._stats_body, bg=C["sidebar"], height=1).pack(fill=tk.X, pady=6)

            # —€—€ Today status —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
            tk.Label(self._stats_body, text="Today",
                     font=("Arial", 10, "bold"),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")

            today_f = tk.Frame(self._stats_body, bg=C["card"])
            today_f.pack(fill=tk.X, pady=(2, 8))

            st_col = status_colors.get(today_status, C["muted"])
            tk.Label(today_f,
                     text=f"  {today_status}  ",
                     font=("Arial", 10, "bold"),
                     bg=st_col, fg="white",
                     relief="flat").pack(side=tk.LEFT)
            tk.Label(today_f,
                     text=f"  In: {today_in}",
                     font=("Arial", 10),
                     bg=C["card"], fg=C["muted"]).pack(side=tk.LEFT)
            if today_out != "—":
                tk.Label(today_f,
                         text=f"  Out: {today_out}",
                         font=("Arial", 10),
                         bg=C["card"], fg=C["muted"]).pack(side=tk.LEFT)

            tk.Frame(self._stats_body, bg=C["sidebar"], height=1).pack(fill=tk.X, pady=4)

            # —€—€ This month attendance —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
            tk.Label(self._stats_body,
                     text=f"This Month ({mo})",
                     font=("Arial", 10, "bold"),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")

            for lbl, val, col in [
                ("Present",  str(present),  C["green"]),
                ("Absent",   str(absent),   C["red"]),
                ("Leave",    str(leave),    C["orange"]),
                ("Att %",    f"{att_pct}%", C["teal"]),
            ]:
                row = tk.Frame(self._stats_body, bg=C["card"])
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=lbl,
                         font=("Arial", 10),
                         bg=C["card"], fg=C["muted"],
                         width=8, anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=val,
                         font=("Arial", 10, "bold"),
                         bg=C["card"], fg=col).pack(side=tk.LEFT)

            tk.Frame(self._stats_body, bg=C["sidebar"], height=1).pack(fill=tk.X, pady=6)

            # —€—€ Sales & Commission —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
            tk.Label(self._stats_body, text="This Month",
                     font=("Arial", 10, "bold"),
                     bg=C["card"], fg=C["muted"]).pack(anchor="w")

            for lbl, val, col in [
                ("Sales",    fmt_currency(mo_sales), C["lime"] if hasattr(C, "lime") else C["green"]),
                ("Comm %",   f"{comm_pct}%",         C["muted"]),
                ("Earned",   fmt_currency(comm_earn), C["teal"]),
            ]:
                row = tk.Frame(self._stats_body, bg=C["card"])
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=lbl,
                         font=("Arial", 10),
                         bg=C["card"], fg=C["muted"],
                         width=8, anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=val,
                         font=("Arial", 10, "bold"),
                         bg=C["card"], fg=col).pack(side=tk.LEFT)

        except Exception as ex:
            app_log(f"[_show_staff_stats] {ex}")

    def _load_tree(self):
        try:
            for i in self.tree.get_children():
                self.tree.delete(i)
            staff_data = get_staff()
            query = getattr(self, "_staff_search_var", None)
            query = query.get().strip().lower() if query else ""
            total = len(staff_data)
            active = 0
            managers = 0
            shown = 0
            for name, s in staff_data.items():
                if s.get("active", True):
                    active += 1
                role = str(s.get("role", ""))
                if role.strip().lower() in {"manager", "lead", "supervisor", "owner"}:
                    managers += 1
                hay = " ".join([
                    str(name),
                    role,
                    str(s.get("phone", "")),
                ]).lower()
                if query and query not in hay:
                    continue
                shown += 1
                self.tree.insert("", tk.END, values=(
                    name,
                    role,
                    s.get("phone", ""),
                    f"{s.get('commission_pct', 0)}%",
                    "✅" if s.get("active", True) else "❌",
                ))
                last_item = self.tree.get_children()[-1]
                values = list(self.tree.item(last_item, "values"))
                is_active = not bool(s.get("inactive", False))
                values[-1] = "Active" if is_active else "Inactive"
                self.tree.item(
                    last_item,
                    values=tuple(values),
                    tags=("active" if is_active else "inactive",),
                )
            for key, val in {
                "total": str(total),
                "active": str(active),
                "managers": str(managers),
            }.items():
                if hasattr(self, "_staff_summary_cards") and key in self._staff_summary_cards:
                    self._staff_summary_cards[key].config(text=val)
            # Phase 5.6.1 Phase 2: update visible result count label
            if hasattr(self, "_staff_result_label"):
                if shown == 0 and query:
                    msg = "No matching staff"
                elif query:
                    msg = f"Showing {shown} of {total} staff member{'s' if shown != 1 else ''}"
                else:
                    msg = f"{total} staff member{'s' if total != 1 else ''}"
                self._staff_result_label.config(text=msg)
        except Exception as e:
            app_log(f"[_load_tree] {e}")

    def _add_dialog(self, staff_name=""):
        if self._rbac_denied(): return
        self._staff_form("Add Staff Member", staff_name)

    def _edit_dialog(self):
        if self._rbac_denied(): return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a staff member.")
            return
        name = self.tree.item(sel[0], "values")[0]
        self._staff_form("Edit Staff Member", name, edit=True)

    def _show_staff_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return "break"
        try:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            self._on_staff_select()
            values = self.tree.item(row_id, "values")
            if not values:
                return "break"
            self._register_staff_context_menu_callbacks()

            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.staff_context_menu import get_sections

            selected_row = {
                "row_id": row_id,
                "name": values[0] if len(values) > 0 else "",
                "role": values[1] if len(values) > 1 else "",
                "phone": values[2] if len(values) > 2 else "",
                "commission": values[3] if len(values) > 3 else "",
                "active": values[4] if len(values) > 4 else "",
            }
            context = build_context(
                "staff",
                entity_type="staff",
                entity_id=selected_row["name"],
                selected_row=selected_row,
                selection_count=1,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TREEVIEW,
                widget_id="staff_directory",
                screen_x=event.x_root,
                screen_y=event.y_root,
                extra={"has_staff": True},
            )
            menu = renderer_service.build_menu(self, get_sections(), context)
            menu.tk_popup(event.x_root, event.y_root)
            return "break"
        except Exception as exc:
            app_log(f"[staff context menu] {exc}")
            return "break"

    def _register_staff_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.staff_context_menu import StaffContextAction

        action_adapter.register(StaffContextAction.EDIT, lambda _ctx, _act: self._edit_dialog())
        action_adapter.register(StaffContextAction.TOGGLE_ACTIVE, lambda _ctx, _act: self._toggle_active())
        action_adapter.register(
            StaffContextAction.COPY_PHONE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("phone", "")),
        )
        action_adapter.register(
            StaffContextAction.COPY_NAME,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("name", "")),
        )
        action_adapter.register(
            StaffContextAction.COPY_ROLE,
            lambda ctx, _act: clipboard_service.copy_text(self, ctx.selected_row.get("role", "")),
        )
        action_adapter.register(StaffContextAction.DELETE, lambda _ctx, _act: self._delete())

    def _staff_form(self, title, name="", edit=False):
        s   = get_staff().get(name, {})
        win = tk.Toplevel(self)
        hide_while_building(win)
        win.title(title)
        popup_window(win, 560, 600)
        win.configure(bg=C["bg"])
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (win.grab_release(), win.destroy()))

        dh = tk.Frame(win, bg=C["sidebar"], padx=20, pady=10)
        dh.pack(fill=tk.X)
        tk.Label(dh, text=title, font=("Arial", 13, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(win, bg=C["teal"], height=2).pack(fill=tk.X)

        f, _canvas, _container = make_scrollable(
            win, bg=C["bg"], padx=30, pady=10)

        entries = {}
        for lbl, key, default in [
            ("Full Name:",          "name",           name),
            ("Role/Designation:",   "role",           s.get("role", "")),
            ("Phone:",              "phone",          s.get("phone", "")),
            ("Commission %:",       "commission_pct", str(s.get("commission_pct", 0))),
            ("Salary (₹/month):",   "salary",         str(s.get("salary", 0))),
            ("Join Date (YYYY-MM-DD):", "join_date",  s.get("join_date", today_str())),
        ]:
            tk.Label(f, text=lbl, bg=C["bg"],
                     fg=C["muted"], font=("Arial", 12)).pack(anchor="w")
            e = tk.Entry(f, font=("Arial", 11), bg=C["input"],
                         fg=C["text"], bd=0, insertbackground=C["accent"])
            e.pack(fill=tk.X, ipady=5, pady=(3, 7))
            e.insert(0, default)
            if edit and key == "name":
                e.config(state="disabled")
            entries[key] = e

        def _save():
            nm   = entries["name"].get().strip()
            role = entries["role"].get().strip()
            ph   = entries["phone"].get().strip()
            comm = safe_float(entries["commission_pct"].get(), 0)
            sal  = safe_float(entries["salary"].get(), 0)
            jd   = entries["join_date"].get().strip()

            if not nm:
                messagebox.showerror("Error", "Name required.")
                return

            try:
                staff = get_staff()
                if not edit and nm in staff:
                    messagebox.showerror("Error", "Staff member already exists.")
                    return
                key = name if edit else nm
                staff[key] = {
                    "role":           role,
                    "phone":          ph,
                    "commission_pct": comm,
                    "salary":         sal,
                    "join_date":      jd,
                    "active":         staff.get(key, {}).get("active", True),
                    "attendance":     staff.get(key, {}).get("attendance", []),
                    "sales":          staff.get(key, {}).get("sales", []),
                }
                save_staff(staff)
                win.grab_release()
                win.destroy()
                self._load_tree()
                messagebox.showinfo("Saved", "Staff saved!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save staff: {e}")

        ModernButton(f, text="💾  Save Staff",
                     command=_save,
                     color=C["teal"], hover_color=C["blue"],
                     width=380, height=38, radius=8,
                     font=("Arial", 11, "bold"),
                     ).pack(fill=tk.X, pady=(4, 0))
        reveal_when_ready(win)

    def _change_photo(self, name: str):
        """Browse and save a staff photo."""
        try:
            path = filedialog.askopenfilename(
                title=f"Select photo for {name}",
                filetypes=[
                    ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                    ("All files", "*.*")
                ]
            )
            if not path:
                return

            # Save photo path in staff data
            staff = get_staff()
            if name in staff:
                staff[name]["photo_path"] = path
                save_staff(staff)
                # Refresh stats panel
                self._show_staff_stats(name)
        except Exception as e:
            messagebox.showerror("Error", f"Could not set photo: {e}")
            app_log(f"[_change_photo] {e}")

    def _toggle_active(self):
        if self._rbac_denied(): return
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0], "values")[0]
        try:
            staff = get_staff()
            key = name
            if key not in staff:
                key = next((k for k in staff if str(k).strip().casefold() == str(name).strip().casefold()), None)
            if not key:
                messagebox.showwarning("Not Found", "Could not find the selected staff member.")
                return
            currently_active = not bool(staff[key].get("inactive", False))
            staff[key]["inactive"] = currently_active
            staff[key]["active"] = not currently_active
            save_staff(staff)
            self._load_tree()
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, "values")
                if values and values[0] == key:
                    self.tree.selection_set(item_id)
                    self.tree.focus(item_id)
                    self.tree.see(item_id)
                    self._on_staff_select()
                    break
            self._show_staff_stats(key)
        except Exception as e:
            messagebox.showerror("Error", f"Could not update status: {e}")

    def _delete(self):
        if self._rbac_denied(): return
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("Delete", f"Delete '{name}'?"):
            try:
                staff = get_staff()
                staff.pop(name, None)
                save_staff(staff)
                self._load_tree()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete: {e}")

    # —€—€ Attendance —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    def _build_attendance(self, parent):
        # —€—€ Tab switcher: Daily view | Performance sheet —€—€
        intro = tk.Frame(parent, bg=C["card"], padx=14, pady=10)
        intro.pack(fill=tk.X, padx=15, pady=(8, 6))
        tk.Label(intro, text="Attendance Workspace",
                 bg=C["card"], fg=C["text"], font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(intro, text="Track daily check-in, clock-out, and attendance performance without leaving the staff module.",
                 bg=C["card"], fg=C["muted"], font=("Arial", 9)).pack(anchor="w", pady=(3, 0))

        tab_row = tk.Frame(parent, bg=C["bg"])
        tab_row.pack(fill=tk.X, padx=15, pady=(8, 0))

        self._att_view = tk.StringVar(value="daily")

        def _switch(view):
            self._att_view.set(view)
            if view == "daily":
                daily_f.pack(fill=tk.BOTH, expand=True)
                perf_f.pack_forget()
                btn_daily.set_color(C["teal"], C["blue"])
                btn_perf.set_color(C["sidebar"], C["blue"])
            else:
                perf_f.pack(fill=tk.BOTH, expand=True)
                daily_f.pack_forget()
                btn_perf.set_color(C["teal"], C["blue"])
                btn_daily.set_color(C["sidebar"], C["blue"])

        btn_daily = ModernButton(tab_row, text="📋  Daily View",
                                 command=lambda: _switch("daily"),
                                 color=C["teal"], hover_color=C["blue"],
                                 width=140, height=32, radius=8,
                                 font=("Arial", 10, "bold"))
        btn_daily.pack(side=tk.LEFT, padx=(0, 4))

        btn_perf = ModernButton(tab_row, text="📊  Performance Sheet",
                                command=lambda: _switch("perf"),
                                color=C["sidebar"], hover_color=C["blue"],
                                width=168, height=32, radius=8,
                                font=("Arial", 10, "bold"))
        btn_perf.pack(side=tk.LEFT)

        # ════════════════════════════════════════
        # DAILY VIEW
        # ════════════════════════════════════════
        daily_f = tk.Frame(parent, bg=C["bg"])
        daily_f.pack(fill=tk.BOTH, expand=True)

        ctrl = tk.Frame(daily_f, bg=C["card"], padx=12, pady=10)
        ctrl.pack(fill=tk.X, padx=15)

        tk.Label(ctrl, text="Date:", bg=C["bg"],
                 fg=C["muted"]).pack(side=tk.LEFT, padx=(0, 4))
        self.att_date = tk.Entry(ctrl, font=("Arial", 12),
                                 bg=C["input"], fg=C["text"],
                                 bd=0, width=14,
                                 insertbackground=C["accent"])
        self.att_date.pack(side=tk.LEFT, ipady=5, padx=(0, 6))
        self.att_date.insert(0, today_str())

        ModernButton(ctrl, text="📋  Load",
                     command=self._load_attendance,
                     color=C["teal"], hover_color=C["blue"],
                     width=80, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.LEFT)

        cols = ("Staff", "Status", "In Time", "Out Time")
        self.att_tree = ttk.Treeview(daily_f, columns=cols,
                                     show="headings", height=10)
        for col, w in zip(cols, [180, 100, 120, 120]):
            self.att_tree.heading(col, text=col)
            self.att_tree.column(col, width=w)
        apply_treeview_column_alignment(self.att_tree)
        self.att_tree.pack(fill=tk.BOTH, expand=True, padx=15)
        self.att_tree.bind("<<TreeviewSelect>>", self._refresh_session_history)

        # Status color tags
        self.att_tree.tag_configure("present", foreground=C["green"])
        self.att_tree.tag_configure("absent",  foreground=C["red"])
        self.att_tree.tag_configure("leave",   foreground=C["orange"])

        bb = tk.Frame(daily_f, bg=C["bg"])
        bb.pack(fill=tk.X, padx=15, pady=8)
        for txt, clr, hclr, cmd in [
            ("✅ Present",   C["green"],  "#1a7a45", lambda: self._mark_att("Present")),
            ("🕐 Clock Out", C["teal"],   C["blue"], self._clock_out),
            ("❌ Absent",    C["red"],    "#c0392b", lambda: self._mark_att("Absent")),
            ("🏖️ Leave",     C["orange"], "#d35400", lambda: self._mark_att("Leave")),
        ]:
            ModernButton(bb, text=txt, command=cmd,
                         color=clr, hover_color=hclr,
                         width=128, height=34, radius=8,
                         font=("Arial", 10, "bold"),
                         ).pack(side=tk.LEFT, padx=3)

        # ════════════════════════════════════════
        # PERFORMANCE SHEET
        # ════════════════════════════════════════
        self._show_session_history = self._is_owner_user()
        if self._show_session_history:
            hist_wrap = tk.Frame(daily_f, bg=C["bg"])
            hist_wrap.pack(fill=tk.BOTH, expand=False, padx=15, pady=(0, 10))
            hist_card = tk.Frame(hist_wrap, bg=C["card"], padx=12, pady=10)
            hist_card.pack(fill=tk.BOTH, expand=True)
            hdr_row = tk.Frame(hist_card, bg=C["card"])
            hdr_row.pack(fill=tk.X)
            tk.Label(hdr_row, text="Today Sessions",
                     bg=C["card"], fg=C["text"],
                     font=("Arial", 11, "bold")).pack(side=tk.LEFT)
            self._session_meta_var = tk.StringVar(value="Select a staff row to view today's login and logout sessions.")
            tk.Label(hdr_row, textvariable=self._session_meta_var,
                     bg=C["card"], fg=C["muted"],
                     font=("Arial", 9)).pack(side=tk.RIGHT)
            s_cols = ("#", "Login", "Logout", "Duration")
            self.session_tree = ttk.Treeview(hist_card, columns=s_cols, show="headings", height=5)
            for col, w, anchor in [
                ("#", 55, "center"),
                ("Login", 120, "center"),
                ("Logout", 120, "center"),
                ("Duration", 120, "center"),
            ]:
                self.session_tree.heading(col, text=col)
                self.session_tree.column(col, width=w, anchor=anchor, stretch=True)
            apply_treeview_column_alignment(self.session_tree)
            self.session_tree.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        perf_f = tk.Frame(parent, bg=C["bg"])
        # not packed by default — shown on tab switch

        # Date range selector
        pr_ctrl = tk.Frame(perf_f, bg=C["bg"], pady=8)
        pr_ctrl.pack(fill=tk.X, padx=15)

        tk.Label(pr_ctrl, text="From:", bg=C["bg"],
                 fg=C["muted"]).pack(side=tk.LEFT, padx=(0, 4))
        self.perf_from = tk.Entry(pr_ctrl, font=("Arial", 11),
                                   bg=C["input"], fg=C["text"],
                                   bd=0, width=12,
                                   insertbackground=C["accent"])
        self.perf_from.pack(side=tk.LEFT, ipady=4, padx=(0, 8))

        tk.Label(pr_ctrl, text="To:", bg=C["bg"],
                 fg=C["muted"]).pack(side=tk.LEFT, padx=(0, 4))
        self.perf_to = tk.Entry(pr_ctrl, font=("Arial", 11),
                                 bg=C["input"], fg=C["text"],
                                 bd=0, width=12,
                                 insertbackground=C["accent"])
        self.perf_to.pack(side=tk.LEFT, ipady=4, padx=(0, 8))

        # Set default: current month
        from datetime import date as _date
        first_day = _date.today().replace(day=1).strftime("%Y-%m-%d")
        self.perf_from.insert(0, first_day)
        self.perf_to.insert(0, today_str())

        ModernButton(pr_ctrl, text="📊  Generate",
                     command=self._gen_perf_sheet,
                     color=C["teal"], hover_color=C["blue"],
                     width=110, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.LEFT, padx=(0, 6))

        # Quick shortcuts
        def _set_month():
            from datetime import date as _d
            self.perf_from.delete(0, "end")
            self.perf_from.insert(0, _d.today().replace(day=1).strftime("%Y-%m-%d"))
            self.perf_to.delete(0, "end")
            self.perf_to.insert(0, today_str())
            self._gen_perf_sheet()

        def _set_last_month():
            from datetime import date as _d
            import calendar
            today = _d.today()
            first = today.replace(day=1)
            last_mo_end = first - timedelta(days=1)
            last_mo_start = last_mo_end.replace(day=1)
            self.perf_from.delete(0, "end")
            self.perf_from.insert(0, last_mo_start.strftime("%Y-%m-%d"))
            self.perf_to.delete(0, "end")
            self.perf_to.insert(0, last_mo_end.strftime("%Y-%m-%d"))
            self._gen_perf_sheet()

        ModernButton(pr_ctrl, text="This Month",
                     command=_set_month,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=100, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.LEFT, padx=(0, 4))

        ModernButton(pr_ctrl, text="Last Month",
                     command=_set_last_month,
                     color=C["sidebar"], hover_color=C["blue"],
                     width=100, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.LEFT)

        # Scrollable table area
        perf_canvas = tk.Canvas(perf_f, bg=C["bg"], highlightthickness=0)
        perf_hsb = ttk.Scrollbar(perf_f, orient="horizontal",
                                  command=perf_canvas.xview)
        perf_vsb = ttk.Scrollbar(perf_f, orient="vertical",
                                  command=perf_canvas.yview)
        perf_canvas.configure(xscrollcommand=perf_hsb.set,
                               yscrollcommand=perf_vsb.set)
        perf_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        perf_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        perf_canvas.pack(fill=tk.BOTH, expand=True, padx=(15, 0))

        self._perf_inner = tk.Frame(perf_canvas, bg=C["bg"])
        self._perf_win   = perf_canvas.create_window(
            (0, 0), window=self._perf_inner, anchor="nw")
        self._perf_inner.bind("<Configure>",
            lambda e: perf_canvas.configure(
                scrollregion=perf_canvas.bbox("all")))
        perf_canvas.bind("<Configure>",
            lambda e: perf_canvas.itemconfig(
                self._perf_win, width=max(e.width, 600)))
        self._perf_canvas = perf_canvas

        # Generate on load
        self._load_attendance()
        self._gen_perf_sheet()

    def _gen_perf_sheet(self):
        """Generate performance sheet for date range."""
        try:
            for w in self._perf_inner.winfo_children():
                w.destroy()

            from_d = self.perf_from.get().strip()
            to_d   = self.perf_to.get().strip()
            staff  = get_staff()

            if not from_d or not to_d:
                return

            # Build date list
            from datetime import datetime as _dt, timedelta as _td
            try:
                d_from = _dt.strptime(from_d, "%Y-%m-%d").date()
                d_to   = _dt.strptime(to_d,   "%Y-%m-%d").date()
            except ValueError:
                tk.Label(self._perf_inner,
                         text="Invalid date format. Use YYYY-MM-DD",
                         bg=C["bg"], fg=C["red"],
                         font=("Arial", 11)).pack(pady=20)
                return

            if d_from > d_to:
                d_from, d_to = d_to, d_from

            dates = []
            cur = d_from
            while cur <= d_to:
                dates.append(cur.strftime("%Y-%m-%d"))
                cur += _td(days=1)

            if not dates:
                return

            # Colors per status
            bg_map = {
                "Present": "#1a4a2a",
                "Absent":  "#4a1a1a",
                "Leave":   "#4a3a10",
                "H":       "#1a2a4a",
            }
            fg_map = {
                "Present": "#4cde82",
                "Absent":  "#ff6b6b",
                "Leave":   "#ffa940",
                "H":       "#64a8e8",
            }

            # Cell size
            CELL_W, CELL_H = 46, 28
            NAME_W = 120
            SUM_W  = 42

            # —€—€ Header row —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
            hdr = tk.Frame(self._perf_inner, bg=C["sidebar"])
            hdr.pack(fill=tk.X)

            tk.Label(hdr, text="Staff",
                     font=("Arial", 10, "bold"),
                     bg=C["sidebar"], fg=C["text"],
                     width=NAME_W//8, anchor="w",
                     padx=8).pack(side=tk.LEFT)

            for d in dates:
                day_num = d[-2:]
                tk.Label(hdr, text=day_num,
                         font=("Arial", 9, "bold"),
                         bg=C["sidebar"], fg=C["muted"],
                         width=CELL_W//8,
                         anchor="center").pack(side=tk.LEFT)

            for lbl in ["P", "A", "L", "%"]:
                tk.Label(hdr, text=lbl,
                         font=("Arial", 9, "bold"),
                         bg=C["sidebar"],
                         fg=C["teal"] if lbl in ("P","%") else C["red"] if lbl=="A" else C["orange"],
                         width=SUM_W//8,
                         anchor="center").pack(side=tk.LEFT)

            tk.Frame(self._perf_inner, bg=C["teal"], height=2).pack(fill=tk.X)

            # —€—€ Staff rows —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
            for idx, (name, s) in enumerate(staff.items()):
                row_bg = C["card"] if idx % 2 == 0 else C["bg"]
                row = tk.Frame(self._perf_inner, bg=row_bg)
                row.pack(fill=tk.X)

                tk.Label(row, text=name,
                         font=("Arial", 10),
                         bg=row_bg, fg=C["text"],
                         width=NAME_W//8, anchor="w",
                         padx=8).pack(side=tk.LEFT)

                att_list = {a.get("date"): a for a in s.get("attendance", [])}
                att_list = {
                    k: attendance_sync_legacy_fields(v)
                    for k, v in att_list.items() if k
                }
                present = absent = leave = 0

                for d in dates:
                    att = att_list.get(d)
                    status = att.get("status", "—") if att else "—"
                    short  = {"Present":"P","Absent":"A","Leave":"L"}.get(status, "—")

                    cell_bg = bg_map.get(status, row_bg)
                    cell_fg = fg_map.get(status, C["muted"])

                    if status == "Present": present += 1
                    elif status == "Absent": absent  += 1
                    elif status == "Leave":  leave   += 1

                    tk.Label(row, text=short,
                             font=("Arial", 9, "bold"),
                             bg=cell_bg, fg=cell_fg,
                             width=CELL_W//8,
                             anchor="center",
                             relief="flat").pack(side=tk.LEFT, padx=1, pady=1)

                # Summary cells
                total  = present + absent + leave
                pct    = int(present / total * 100) if total else 0

                for val, col in [
                    (str(present), C["green"]),
                    (str(absent),  C["red"]),
                    (str(leave),   C["orange"]),
                    (f"{pct}%",    C["teal"]),
                ]:
                    tk.Label(row, text=val,
                             font=("Arial", 9, "bold"),
                             bg=row_bg, fg=col,
                             width=SUM_W//8,
                             anchor="center").pack(side=tk.LEFT)

            # —€—€ Total row —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
            tk.Frame(self._perf_inner, bg=C["teal"], height=1).pack(fill=tk.X, pady=(4, 0))
            tot_row = tk.Frame(self._perf_inner, bg=C["sidebar"])
            tot_row.pack(fill=tk.X)

            tk.Label(tot_row, text="TOTAL",
                     font=("Arial", 10, "bold"),
                     bg=C["sidebar"], fg=C["accent"],
                     width=NAME_W//8, anchor="w",
                     padx=8).pack(side=tk.LEFT)

            all_att = {name: {a.get("date"): a for a in s.get("attendance", [])}
                       for name, s in staff.items()}
            all_att = {
                name: {
                    k: attendance_sync_legacy_fields(v)
                    for k, v in s_att.items() if k
                }
                for name, s_att in all_att.items()
            }

            for d in dates:
                day_p = sum(1 for s_att in all_att.values()
                            if s_att.get(d, {}).get("status") == "Present")
                total_s = len(staff)
                cell_bg = C["sidebar"]
                cell_fg = C["green"] if day_p == total_s else C["muted"] if day_p == 0 else C["text"]
                tk.Label(tot_row, text=str(day_p),
                         font=("Arial", 9),
                         bg=cell_bg, fg=cell_fg,
                         width=CELL_W//8,
                         anchor="center").pack(side=tk.LEFT)

            for _ in range(4):
                tk.Label(tot_row, text="",
                         bg=C["sidebar"],
                         width=SUM_W//8).pack(side=tk.LEFT)

        except Exception as ex:
            app_log(f"[_gen_perf_sheet] {ex}")

    def _load_attendance(self):
        try:
            for i in self.att_tree.get_children():
                self.att_tree.delete(i)
            dt    = self.att_date.get().strip()
            staff = get_staff()
            for name, s in staff.items():
                att_today = attendance_get_day_record(
                    s.get("attendance", []), dt)
                latest = None
                if att_today:
                    att_today = attendance_sync_legacy_fields(att_today)
                    latest = attendance_latest_session(att_today)
                status = att_today.get("status", "—") if att_today else "—"
                in_t   = latest.get("in_time", "") if latest else (
                    att_today.get("in_time", "") if att_today else "")
                out_t  = latest.get("out_time", "") if latest else (
                    att_today.get("out_time", "") if att_today else "")
                tag    = {"Present":"present","Absent":"absent","Leave":"leave"}.get(status,"")
                self.att_tree.insert("", tk.END,
                                      values=(name, status, in_t, out_t),
                                      tags=(tag,) if tag else ())
            rows = self.att_tree.get_children()
            if rows:
                self.att_tree.selection_set(rows[0])
                self.att_tree.focus(rows[0])
            self._refresh_session_history()
        except Exception as e:
            app_log(f"[_load_attendance] {e}")

    def _mark_att(self, status: str):
        """
        Bug 15 fix: do NOT set out_time when marking Present/Absent/Leave.
        out_time is only set via _clock_out().
        in_time is only set when marking Present (first time).
        """
        sel = self.att_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a staff member.")
            return
        name  = self.att_tree.item(sel[0], "values")[0]
        dt    = self.att_date.get().strip()
        staff = get_staff()
        if name not in staff:
            return
        att = staff[name].setdefault("attendance", [])
        now = datetime.now().strftime("%H:%M")

        existing = attendance_get_day_record(att, dt)
        if existing:
            existing["status"] = status
            existing = attendance_sync_legacy_fields(existing)
            if status == "Present" and not attendance_open_session(existing):
                sessions = attendance_get_sessions(existing)
                sessions.append({
                    "in_time": now,
                    "out_time": "",
                })
                existing["sessions"] = sessions
                attendance_sync_legacy_fields(existing)
        else:
            day_rec = {
                "date":   dt,
                "status": status,
            }
            if status == "Present":
                day_rec["sessions"] = [{
                    "in_time": now,
                    "out_time": "",
                }]
            att.append(attendance_sync_legacy_fields(day_rec))

        try:
            save_staff(staff)
            self._load_attendance()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save attendance: {e}")

    def _clock_out(self):
        """Separate clock-out — records out_time properly."""
        sel = self.att_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a staff member.")
            return
        name  = self.att_tree.item(sel[0], "values")[0]
        dt    = self.att_date.get().strip()
        staff = get_staff()
        if name not in staff:
            return
        att = staff[name].get("attendance", [])
        now = datetime.now().strftime("%H:%M")

        existing = attendance_get_day_record(att, dt)
        if existing:
            existing = attendance_sync_legacy_fields(existing)
            if existing.get("status") != "Present":
                messagebox.showwarning(
                    "Not Clocked In",
                    f"{name} is not marked Present today.")
                return
            open_session = attendance_open_session(existing)
            if not open_session:
                messagebox.showwarning(
                    "Not Clocked In",
                    f"{name} has no open session for today.")
                return
            open_session["out_time"] = now
            attendance_sync_legacy_fields(existing)
            try:
                save_staff(staff)
                self._load_attendance()
                messagebox.showinfo("Clocked Out",
                                    f"{name} clocked out at {now}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save clock-out: {e}")
        else:
            messagebox.showwarning(
                "Not Found",
                f"{name} has no attendance record for {dt}.\n"
                "Mark Present first.")

    # —€—€ Commission —€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€—€
    def _build_commission(self, parent):
        intro = tk.Frame(parent, bg=C["card"], padx=14, pady=10)
        intro.pack(fill=tk.X, padx=15, pady=(8, 6))
        tk.Label(intro, text="Commission Workspace",
                 bg=C["card"], fg=C["text"], font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(intro, text="Review staff sales contribution and payout estimates for each month in one clean report.",
                 bg=C["card"], fg=C["muted"], font=("Arial", 9)).pack(anchor="w", pady=(3, 0))

        ctrl = tk.Frame(parent, bg=C["card"], padx=12, pady=10)
        ctrl.pack(fill=tk.X, padx=15)

        tk.Label(ctrl, text="Month (YYYY-MM):", bg=C["bg"],
                 fg=C["muted"]).pack(side=tk.LEFT, padx=(0, 4))
        self.comm_month = tk.Entry(ctrl, font=("Arial", 12),
                                   bg=C["input"], fg=C["text"],
                                   bd=0, width=12,
                                   insertbackground=C["accent"])
        self.comm_month.pack(side=tk.LEFT, ipady=5, padx=(0, 10))
        self.comm_month.insert(0, month_str())

        ModernButton(ctrl, text="📊  Calculate",
                     command=self._calc_commission,
                     color=C["teal"], hover_color=C["blue"],
                     width=110, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.LEFT)

        cols = ("Staff", "Role", "Commission %", "Month Sales",
                "Commission Earned")
        self.comm_tree = ttk.Treeview(parent, columns=cols,
                                      show="headings", height=14)
        for col, w in zip(cols, [160, 120, 110, 120, 140]):
            self.comm_tree.heading(col, text=col)
            self.comm_tree.column(col, width=w)
        apply_treeview_column_alignment(self.comm_tree)
        self.comm_tree.pack(fill=tk.BOTH, expand=True, padx=15)

        tk.Label(parent,
                 text="Note: Staff sales are tracked when billing staff "
                      "name is entered.",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11)).pack(pady=5)

        self._calc_commission()

    def _calc_commission(self):
        """
        Bug 14 fix: removed unused month_total CSV read.
        Commission comes from staff["sales"] records only.
        """
        try:
            for i in self.comm_tree.get_children():
                self.comm_tree.delete(i)
            mo    = self.comm_month.get().strip()
            staff = get_staff()
            for name, s in staff.items():
                comm_pct    = safe_float(s.get("commission_pct", 0))
                staff_sales = sum(
                    safe_float(sale.get("amount", 0))
                    for sale in s.get("sales", [])
                    if sale.get("month", "") == mo
                )
                comm_earned = staff_sales * comm_pct / 100
                self.comm_tree.insert("", tk.END, values=(
                    name,
                    s.get("role", ""),
                    f"{comm_pct}%",
                    fmt_currency(staff_sales),
                    fmt_currency(comm_earned),
                ))
        except Exception as e:
            app_log(f"[_calc_commission] {e}")

    def refresh(self):
        self._load_tree()
        # Refresh attendance + perf sheet if visible
        try:
            self._load_attendance()
        except Exception:
            pass
        try:
            self._gen_perf_sheet()
        except Exception:
            pass

# v5 staff compatibility overrides -------------------------------------------
def get_staff() -> dict:
    from adapters.staff_adapter import get_staff_legacy_map_v5, use_v5_staff_db
    if use_v5_staff_db():
        return get_staff_legacy_map_v5()
    return load_json(F_STAFF, {})


def save_staff(data: dict) -> bool:
    from adapters.staff_adapter import save_staff_legacy_map_v5, use_v5_staff_db
    if use_v5_staff_db():
        save_staff_legacy_map_v5(data)
        return True
    return save_json(F_STAFF, data)
