"""
google_backup.py  –  BOBY'S Salon
Google Drive real-time backup.
Setup once → auto-backup on every bill save.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, threading, json, time
from utils import (C, DATA_DIR, load_json, save_json, now_str, app_log)
from ui_theme import ModernButton
from branding import get_backup_folder_name

F_GDRIVE_CFG = os.path.join(DATA_DIR, "gdrive_config.json")
GDRIVE_TOKEN_JSON = os.path.join(DATA_DIR, "gdrive_token.json")
LEGACY_GDRIVE_TOKEN_PICKLE = os.path.join(DATA_DIR, "gdrive_token.pickle")

# Files to back up
BACKUP_FILES = [
    "sales_report.csv",
    "customers.json",
    "expenses.json",
    "appointments.json",
    "staff.json",
    "inventory.json",
    "memberships.json",
    "redeem_codes.json",
    "services_db.json",
    "offers.json",
]


# ─────────────────────────────────────────
#  GOOGLE DRIVE API HELPERS
# ─────────────────────────────────────────
def _get_service():
    """Build Google Drive service. Requires credentials.json."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Google API libraries not installed.\n"
            "Run:\n"
            "pip install google-api-python-client "
            "google-auth-httplib2 google-auth-oauthlib")

    SCOPES     = ["https://www.googleapis.com/auth/drive.file"]
    creds_file = os.path.join(DATA_DIR, "credentials.json")

    creds = _load_google_credentials(Credentials)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_file):
                raise FileNotFoundError(
                    "credentials.json not found!\n\n"
                    "Please follow setup steps in Settings → "
                    "Google Backup tab.")
            flow  = InstalledAppFlow.from_client_secrets_file(
                creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        _save_google_credentials(creds)

    return build("drive", "v3", credentials=creds)


def _load_google_credentials(credentials_cls):
    if os.path.exists(GDRIVE_TOKEN_JSON):
        return credentials_cls.from_authorized_user_file(
            GDRIVE_TOKEN_JSON,
            ["https://www.googleapis.com/auth/drive.file"],
        )
    return _migrate_legacy_pickle_token(credentials_cls)


def _save_google_credentials(creds) -> None:
    with open(GDRIVE_TOKEN_JSON, "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def _migrate_legacy_pickle_token(credentials_cls):
    if not os.path.exists(LEGACY_GDRIVE_TOKEN_PICKLE):
        return None
    try:
        import pickle

        with open(LEGACY_GDRIVE_TOKEN_PICKLE, "rb") as f:
            legacy_creds = pickle.load(f)
        if not legacy_creds:
            return None
        _save_google_credentials(legacy_creds)
        try:
            os.replace(LEGACY_GDRIVE_TOKEN_PICKLE, LEGACY_GDRIVE_TOKEN_PICKLE + ".migrated")
        except Exception:
            pass
        return credentials_cls.from_authorized_user_file(
            GDRIVE_TOKEN_JSON,
            ["https://www.googleapis.com/auth/drive.file"],
        )
    except Exception as e:
        app_log(f"[google backup] legacy pickle token migration skipped: {e}")
        return None


def _get_or_create_folder(service, folder_name: str) -> str:
    """Get Drive folder ID, create if not exists."""
    query = (f"name='{folder_name}' and "
             f"mimeType='application/vnd.google-apps.folder' and "
             f"trashed=false")
    results = service.files().list(q=query, spaces="drive",
                                    fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    # Create
    meta = {"name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=meta,
                                     fields="id").execute()
    return folder.get("id")


def backup_file(service, local_path: str,
                folder_id: str) -> bool:
    """Upload or update a file in Drive folder."""
    from googleapiclient.http import MediaFileUpload
    import mimetypes

    fname    = os.path.basename(local_path)
    mime, _  = mimetypes.guess_type(local_path)
    mime     = mime or "application/octet-stream"
    media    = MediaFileUpload(local_path, mimetype=mime,
                                resumable=True)

    # Check if file already exists in folder
    query = (f"name='{fname}' and "
             f"'{folder_id}' in parents and "
             f"trashed=false")
    existing = service.files().list(
        q=query, fields="files(id)").execute().get("files", [])

    if existing:
        # Update existing
        service.files().update(
            fileId=existing[0]["id"],
            media_body=media).execute()
    else:
        # Create new
        meta = {"name": fname, "parents": [folder_id]}
        service.files().create(
            body=meta, media_body=media,
            fields="id").execute()
    return True


def backup_all(progress_cb=None, done_cb=None):
    """
    Backup all app data files to Google Drive.
    Runs in a background thread.
    """
    def _worker():
        try:
            service   = _get_service()
            folder_id = _get_or_create_folder(
                service, get_backup_folder_name())

            total   = len(BACKUP_FILES)
            success = 0

            for i, fname in enumerate(BACKUP_FILES):
                fpath = os.path.join(DATA_DIR, fname)
                if not os.path.exists(fpath):
                    if progress_cb:
                        progress_cb(i+1, total, fname, "skipped")
                    continue
                try:
                    backup_file(service, fpath, folder_id)
                    success += 1
                    if progress_cb:
                        progress_cb(i+1, total, fname, "ok")
                except Exception as e:
                    if progress_cb:
                        progress_cb(i+1, total, fname,
                                     f"error: {e}")

            # Save last backup time
            save_json(F_GDRIVE_CFG, {
                "last_backup": now_str(),
                "folder_id":   folder_id,
                "success":     success,
                "total":       total,
            })

            if done_cb:
                try:
                    done_cb(True, success, total)
                except Exception as e:
                    app_log(f"[backup_all done_cb] {e}")

        except Exception as e:
            app_log(f"[backup_all error] {e}")
            if done_cb:
                try:
                    done_cb(False, 0, 0, str(e))
                except Exception as e2:
                    app_log(f"[backup_all error done_cb] {e2}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def get_last_backup_time() -> str:
    cfg = load_json(F_GDRIVE_CFG, {})
    return cfg.get("last_backup", "Never")


# ─────────────────────────────────────────
#  GOOGLE BACKUP SETTINGS FRAME
# ─────────────────────────────────────────
class GoogleBackupFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="☁️  Google Drive Backup",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT, padx=20)

        # Scrollable body
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical",
                                command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)
        f   = tk.Frame(canvas, bg=C["bg"], padx=30, pady=20)
        cw  = canvas.create_window((0,0), window=f, anchor="nw")
        f.bind("<Configure>",
               lambda e: canvas.configure(
                   scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(cw, width=e.width))

        # ── Status card ──────────────────────────
        status_f = tk.Frame(f, bg=C["card"], padx=20, pady=14)
        status_f.pack(fill=tk.X, pady=(0, 20))

        self.status_lbl = tk.Label(
            status_f, text="",
            font=("Arial", 11, "bold"),
            bg=C["card"], fg=C["lime"])
        self.status_lbl.pack(anchor="w")

        self.last_lbl = tk.Label(
            status_f, text=f"Last backup: {get_last_backup_time()}",
            font=("Arial", 11), bg=C["card"], fg=C["muted"])
        self.last_lbl.pack(anchor="w", pady=(4, 0))

        self._check_setup_status(status_f)

        # ── Setup Instructions ───────────────────
        tk.Label(f, text="📋  Setup Instructions",
                 font=("Arial", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(anchor="w",
                                                 pady=(0, 8))

        steps = [
            ("Step 1", "Google Cloud Console-ൽ പോകൂ:\nhttps://console.cloud.google.com",
             C["blue"]),
            ("Step 2", "New Project create ചെയ്യൂ → "
                        "APIs & Services → Enable APIs\n"
                        "→ 'Google Drive API' search ചെയ്ത് Enable ചെയ്യൂ",
             C["blue"]),
            ("Step 3", "Credentials → Create Credentials → "
                        "OAuth Client ID\n"
                        "→ Desktop App → Download JSON",
             C["blue"]),
            ("Step 4", "Downloaded file-ന്റെ name 'credentials.json' "
                        "ആക്കൂ\n"
                        "→ ഈ button click ചെയ്ത് select ചെയ്യൂ:",
             C["teal"]),
        ]

        for title, desc, col in steps:
            card = tk.Frame(f, bg=C["card"], padx=14, pady=10)
            card.pack(fill=tk.X, pady=(0, 8))
            tk.Label(card, text=title,
                     font=("Arial", 12, "bold"),
                     bg=C["card"], fg=col).pack(anchor="w")
            tk.Label(card, text=desc,
                     font=("Arial", 11),
                     bg=C["card"], fg=C["text"],
                     justify="left").pack(anchor="w", pady=(3,0))

        # Browse credentials button
        ModernButton(f, text="📂  Select credentials.json",
                     command=self._browse_credentials,
                     color=C["teal"], hover_color=C["blue"],
                     width=220, height=36, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(anchor="w", pady=(0, 20))

        # Credentials status
        creds_path = os.path.join(DATA_DIR, "credentials.json")
        creds_ok   = os.path.exists(creds_path)
        self.creds_lbl = tk.Label(
            f,
            text=("✅  credentials.json found!"
                  if creds_ok
                  else "⚠️  credentials.json not found"),
            font=("Arial", 12, "bold"),
            bg=C["bg"],
            fg=C["lime"] if creds_ok else C["orange"])
        self.creds_lbl.pack(anchor="w", pady=(0, 20))

        # Manual backup button
        ModernButton(f, text="☁️  Backup Now",
                     command=self._backup_now,
                     color=C["purple"], hover_color="#6c3483",
                     width=160, height=38, radius=8,
                     font=("Arial", 11, "bold"),
                     ).pack(anchor="w")

        # Auto backup toggle
        ab_row = tk.Frame(f, bg=C["bg"])
        ab_row.pack(fill=tk.X, pady=(16, 0))
        self.auto_var = tk.BooleanVar(
            value=load_json(F_GDRIVE_CFG, {}).get("auto", False))
        tk.Checkbutton(ab_row,
                       text="Auto backup after every bill save",
                       variable=self.auto_var,
                       command=self._toggle_auto,
                       bg=C["bg"], fg=C["text"],
                       selectcolor=C["input"],
                       font=("Arial", 12),
                       cursor="hand2").pack(side=tk.LEFT)

        # Progress log
        tk.Label(f, text="Backup Log:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 12, "bold")).pack(anchor="w",
                                                   pady=(20, 4))
        self.log_txt = tk.Text(f, height=8,
                                font=("Courier New", 11),
                                bg=C["input"], fg=C["text"],
                                bd=0, state="disabled")
        self.log_txt.pack(fill=tk.X)

    def _check_setup_status(self, parent):
        if os.path.exists(GDRIVE_TOKEN_JSON) or os.path.exists(LEGACY_GDRIVE_TOKEN_PICKLE):
            self.status_lbl.config(
                text="✅  Google Drive Connected",
                fg=C["lime"])
        else:
            self.status_lbl.config(
                text="⚠️  Not connected — Follow setup steps below",
                fg=C["orange"])

    def _browse_credentials(self):
        path = filedialog.askopenfilename(
            title="Select credentials.json",
            filetypes=[("JSON files","*.json"), ("All files","*.*")])
        if path:
            import shutil
            dest = os.path.join(DATA_DIR, "credentials.json")
            shutil.copy(path, dest)
            self.creds_lbl.config(
                text="✅  credentials.json saved!",
                fg=C["lime"])
            messagebox.showinfo("Done",
                                 "credentials.json saved!\n"
                                 "Click 'Backup Now' to authorize "
                                 "and start backup.")

    def _toggle_auto(self):
        cfg = load_json(F_GDRIVE_CFG, {})
        cfg["auto"] = self.auto_var.get()
        save_json(F_GDRIVE_CFG, cfg)

    def _log(self, msg: str):
        self.log_txt.config(state="normal")
        self.log_txt.insert("end", f"{msg}\n")
        self.log_txt.see("end")
        self.log_txt.config(state="disabled")

    def _backup_now(self):
        self._log(f"\n[{now_str()}] Starting backup...")

        def progress(i, total, fname, status):
            icon = "✅" if status=="ok" else ("⏭" if status=="skipped" else "❌")
            self.after(0, lambda: self._log(
                f"  {icon} {fname} ({i}/{total})"))

        def done(ok, success, total, err=""):
            if ok:
                self.after(0, lambda: (
                    self._log(f"✅ Backup complete! {success}/{total} files"),
                    self.last_lbl.config(
                        text=f"Last backup: {now_str()}"),
                    self.status_lbl.config(
                        text="✅  Google Drive Connected",
                        fg=C["lime"]),
                    messagebox.showinfo("Backup Complete",
                                         f"✅ {success}/{total} files backed up to Google Drive!")
                ))
            else:
                self.after(0, lambda: (
                    self._log(f"❌ Backup failed: {err}"),
                    messagebox.showerror("Backup Failed",
                                          f"Could not backup:\n{err}\n\n"
                                          f"Check setup instructions.")
                ))

        backup_all(progress_cb=progress, done_cb=done)

    def refresh(self):
        self.last_lbl.config(
            text=f"Last backup: {get_last_backup_time()}")


def auto_backup_if_enabled():
    """Call this after every bill save."""
    cfg = load_json(F_GDRIVE_CFG, {})
    if cfg.get("auto", False):
        backup_all()
