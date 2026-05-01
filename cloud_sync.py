"""
cloud_sync.py  Ã¢â‚¬â€œ  BOBY'S Salon : Cloud & Network Sync
Options:
  1. OneDrive / Dropbox / Google Drive Desktop Ã¢â‚¬â€ folder sync
  2. Auto copy to any folder (USB, NAS, custom path)
  3. LAN Web Viewer Ã¢â‚¬â€ view reports from mobile on same WiFi
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, shutil, threading, json, time, urllib.request, hashlib, secrets
# H2 FIX: secrets module used for unpredictable Flask secret_key below
from utils import (C, DATA_DIR, load_json, save_json,
                   app_log,
                   now_str, today_str, F_REPORT)
from ui_theme import ModernButton
from icon_system import get_action_icon, get_section_icon
from backup_system import (
    backup_destination,
    get_backup_config,
    normalize_backup_folder,
    save_backup_config,
    sync_offline_backup,
    restore_from_backup,
    schedule_offline_backup,
)
from branding import get_app_name, get_company_name, get_backup_folder_name

F_SYNC_CFG = os.path.join(DATA_DIR, "sync_config.json")

BACKUP_FILES = [
    "sales_report.csv", "customers.json", "expenses.json",
    "appointments.json", "staff.json", "inventory.json",
    "memberships.json", "redeem_codes.json", "offers.json",
    "services_db.json", "pkg_templates.json",
]

# Common cloud folder paths
CLOUD_SUGGESTIONS = {
    "OneDrive":       os.path.join(os.path.expanduser("~"), "OneDrive"),
    "OneDrive (Work)":os.path.join(os.path.expanduser("~"), "OneDrive - Company"),
    "Dropbox":        os.path.join(os.path.expanduser("~"), "Dropbox"),
    "Google Drive":   os.path.join(os.path.expanduser("~"), "Google Drive"),
    "iCloud Drive":   os.path.join(os.path.expanduser("~"), "iCloudDrive"),
}


def get_sync_config() -> dict:
    return load_json(F_SYNC_CFG, {
        "folder":      "",
        "auto_sync":   False,
        "lan_enabled": False,
        "lan_port":    5050,
        "lan_pin":     "",
        "lan_session_minutes": 15,
        "last_sync":   "",
    })

def save_sync_config(cfg: dict):
    save_json(F_SYNC_CFG, cfg)


def sync_to_folder(folder: str, progress_cb=None) -> tuple:
    """Copy all data files to target folder. Returns (success_count, errors)."""
    if not folder or not os.path.exists(folder):
        return 0, ["Target folder does not exist."]

    dest = os.path.join(folder, get_backup_folder_name())
    os.makedirs(dest, exist_ok=True)

    # Also copy Bills folder
    bills_src = os.path.join(DATA_DIR, "Bills")
    bills_dst = os.path.join(dest, "Bills")
    os.makedirs(bills_dst, exist_ok=True)

    success = 0
    errors  = []

    for fname in BACKUP_FILES:
        src = os.path.join(DATA_DIR, fname)
        if os.path.exists(src):
            try:
                shutil.copy2(src, os.path.join(dest, fname))
                success += 1
                if progress_cb: progress_cb(fname, "ok")
            except Exception as e:
                errors.append(f"{fname}: {e}")
                if progress_cb: progress_cb(fname, "error")

    # Copy recent bills (last 30 PDFs)
    if os.path.exists(bills_src):
        pdfs = sorted([f for f in os.listdir(bills_src) if f.endswith(".pdf")])[-30:]
        for pdf in pdfs:
            try:
                shutil.copy2(os.path.join(bills_src, pdf),
                              os.path.join(bills_dst, pdf))
            except Exception:
                pass

    cfg = get_sync_config()
    cfg["last_sync"] = now_str()
    save_sync_config(cfg)

    return success, errors


def auto_sync():
    """Called after every bill save if auto_sync is enabled.

    Phase 3B FIX: Uses submit_background_task from the bounded worker
    pool instead of spawning an unbounded thread. This prevents thread
    accumulation when multiple bills save in quick succession.
    """
    from worker_pool import submit_background_task
    submit_background_task(
        fn=_exec_auto_sync,
        label="auto_sync",
    )


def _exec_auto_sync():
    """Phase 3B: Actual auto_sync work, runs in worker pool thread."""
    cfg = get_sync_config()
    if cfg.get("auto_sync") and cfg.get("folder"):
        try:
            sync_to_folder(cfg["folder"])
        except Exception as e:
            app_log(f"[auto_sync] sync_to_folder failed: {e}")


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  LAN WEB VIEWER
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
_lan_server = None
_lan_state = {
    "thread": None,
    "enabled": False,
    "pin": "",
    "session_minutes": 15,
    "port": 5050,
    "ip": "localhost",
}


def _build_lan_lockout_test_app(pin: str = "1234", port: int = 5050, session_minutes: int = 15):
    from flask import Flask, render_template_string, request, session

    app = Flask(__name__)
    # H2 FIX: Use cryptographically random secret key instead of PIN-derived hash.
    # The previous code used sha256(DATA_DIR|PIN|PORT|...) which allowed anyone
    # who knew the 4-digit PIN to compute the secret_key and forge Flask sessions.
    app.secret_key = secrets.token_hex(32)
    lan_attempts = {}
    max_attempts = 5
    window_seconds = 10 * 60
    lockout_seconds = 10 * 60
    _lan_state.update({
        "enabled": True,
        "pin": str(pin or "").strip(),
        "session_minutes": max(5, int(session_minutes or 15)),
        "port": port,
    })

    login_html = "<html><body><div>{{ error or '' }}</div><div>{{ hint or '' }}</div></body></html>"

    def _client_ip() -> str:
        forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return forwarded or request.remote_addr or "unknown"

    def _read_lan_attempt_state(ip: str) -> dict:
        entry = lan_attempts.get(ip, {"attempts": [], "locked_until": 0.0})
        now = time.time()
        attempts = [ts for ts in entry.get("attempts", []) if now - ts <= window_seconds]
        locked_until = float(entry.get("locked_until", 0.0) or 0.0)
        if locked_until and locked_until <= now:
            locked_until = 0.0
        clean = {"attempts": attempts, "locked_until": locked_until}
        if attempts or locked_until:
            lan_attempts[ip] = clean
        else:
            lan_attempts.pop(ip, None)
        return clean

    def _lan_lock_message(locked_until: float) -> str:
        remaining = max(1, int((locked_until - time.time()) // 60) + 1)
        return f"Too many failed PIN attempts. Try again in about {remaining} minute(s)."

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = ""
        hint = ""
        ip = _client_ip()
        state = _read_lan_attempt_state(ip)
        if state.get("locked_until", 0.0):
            msg = _lan_lock_message(state["locked_until"])
            return render_template_string(login_html, error=msg, hint=""), 429, {"Retry-After": str(lockout_seconds)}
        if request.method == "POST":
            entered = str(request.form.get("pin", "")).strip()
            if entered == _lan_state.get("pin", ""):
                lan_attempts.pop(ip, None)
                session["lan_auth_at"] = time.time()
                return "OK", 200
            attempts = state.get("attempts", [])
            attempts.append(time.time())
            if len(attempts) >= max_attempts:
                locked_until = time.time() + lockout_seconds
                lan_attempts[ip] = {"attempts": attempts, "locked_until": locked_until}
                msg = _lan_lock_message(locked_until)
                return render_template_string(login_html, error=msg, hint=""), 429, {"Retry-After": str(lockout_seconds)}
            lan_attempts[ip] = {"attempts": attempts, "locked_until": 0.0}
            remaining = max(0, max_attempts - len(attempts))
            error = "Invalid PIN."
            hint = f"{remaining} attempt(s) left before temporary lock."
        return render_template_string(login_html, error=error, hint=hint)

    app.config["LAN_ATTEMPTS"] = lan_attempts
    app.config["LAN_LOCKOUT_SECONDS"] = lockout_seconds
    return app


def start_lan_server(
    port: int = 5050,
    pin: str = "",
    session_minutes: int = 15,
    allow_network_access: bool = False,
):
    """Start a simple Flask web server for LAN/mobile viewer access.

    H3 FIX: By default (allow_network_access=False) the server binds only
    to 127.0.0.1 (localhost). This means only the local machine can
    access the viewer. To expose it on the LAN, the caller must explicitly
    set allow_network_access=True. Previous behavior (0.0.0.0) was exposing
    all billing data to anyone on the local network/WiFi."""
    global _lan_server
    pin = str(pin or "").strip()
    if len(pin) < 4:
        return None, "Set a LAN Viewer PIN with at least 4 digits."
    try:
        from flask import Flask, render_template_string, jsonify, request, redirect, session, url_for, abort
        import csv, socket
    except ImportError:
        return None, "Flask not installed. Run: pip install flask"

    # H3 FIX: Default to localhost-only; only bind 0.0.0.0 when explicitly allowed
    lan_host = "0.0.0.0" if allow_network_access else "127.0.0.1"

    _lan_state.update({
        "enabled": True,
        "pin": pin,
        "session_minutes": max(5, int(session_minutes or 15)),
        "port": port,
        "allow_network_access": allow_network_access,
        "host": lan_host,
    })

    if _lan_state.get("thread") is not None and _lan_state["thread"].is_alive():
        return _lan_state.get("ip", "localhost"), None

    app = Flask(__name__)
    # H2 FIX: Cryptographically random secret key (see comment at line 139).
    app.secret_key = secrets.token_hex(32)
    lan_attempts = {}
    max_attempts = 5
    window_seconds = 10 * 60
    lockout_seconds = 10 * 60

    app_name = get_app_name()
    company_name = get_company_name()

    HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__APP_TITLE__</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; background: #1a1a2e; color: #e8e8e8; }
.header { background: #16213e; padding: 16px 20px; display:flex; align-items:center; gap:12px; }
.header h1 { font-size: 1.3em; color: #ff79c6; }
.cards { display: flex; flex-wrap: wrap; gap: 12px; padding: 16px; }
.card { background: #16213e; border-radius: 10px; padding: 16px 20px; min-width: 140px; flex:1; }
.card .val { font-size: 1.5em; font-weight: bold; color: #50fa7b; }
.card .lbl { font-size: 0.8em; color: #94a3b8; margin-top: 4px; }
.section { padding: 0 16px 16px; }
.section h2 { font-size: 1em; color: #ff79c6; margin-bottom: 10px; }
table { width: 100%; border-collapse: collapse; background: #16213e; border-radius: 8px; overflow: hidden; font-size: 0.85em; }
th { background: #0f3460; padding: 10px 12px; text-align: left; color: #94a3b8; }
td { padding: 8px 12px; border-bottom: 1px solid #2d2d44; }
tr:last-child td { border: none; }
.badge { display:inline-block; padding:2px 8px; border-radius:12px; font-size:0.75em; }
.cash { background:#16a085; } .card-pay { background:#2980b9; } .upi { background:#8e44ad; }
</style>
</head>
<body>
<div class="header"><h1>__COMPANY_NAME__</h1></div>
<div id="app"></div>
<script>
async function load() {
  const res  = await fetch('/api/summary');
  const data = await res.json();
  const res2 = await fetch('/api/bills');
  const bills = await res2.json();
  
  document.getElementById('app').innerHTML = `
    <div class="cards">
      <div class="card"><div class="val">Rs${data.today_rev.toLocaleString()}</div><div class="lbl">Today Revenue</div></div>
      <div class="card"><div class="val">${data.today_bills}</div><div class="lbl">Today Bills</div></div>
      <div class="card"><div class="val">Rs${data.month_rev.toLocaleString()}</div><div class="lbl">Month Revenue</div></div>
      <div class="card"><div class="val">Rs${data.all_rev.toLocaleString()}</div><div class="lbl">All Time</div></div>
    </div>
    <div class="section">
      <h2>Recent Bills</h2>
      <table>
        <tr><th>Date</th><th>Invoice</th><th>Customer</th><th>Payment</th><th>Total</th></tr>
        ${bills.slice(0,30).map(b => `
          <tr>
            <td>${b.date}</td>
            <td>${b.invoice}</td>
            <td>${b.name}</td>
            <td><span class="badge ${b.payment.toLowerCase()==='cash'?'cash':b.payment.toLowerCase()==='upi'?'upi':'card-pay'}">${b.payment}</span></td>
            <td>Rs${parseFloat(b.total).toFixed(2)}</td>
          </tr>`).join('')}
      </table>
    </div>`;
}
load();
setInterval(load, 30000);
</script>
</body>
</html>""".replace("__APP_TITLE__", app_name).replace("__COMPANY_NAME__", company_name)

    LOGIN_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__APP_TITLE__ Mobile Viewer Login</title>
<style>
body { font-family: Arial, sans-serif; background: #111827; color: #f3f4f6; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }
.card { width:min(92vw, 360px); background:#1f2937; border-radius:14px; padding:24px; box-shadow:0 12px 30px rgba(0,0,0,0.25); }
h1 { margin:0 0 10px; font-size:1.2rem; } p { color:#9ca3af; line-height:1.45; }
input { width:100%; padding:12px 14px; border:none; border-radius:10px; font-size:1rem; margin:12px 0; }
button { width:100%; padding:12px 14px; border:none; border-radius:10px; background:#3b82f6; color:#fff; font-weight:bold; cursor:pointer; }
.err { color:#f87171; margin-top:8px; min-height:1.2em; }
.hint { color:#fbbf24; margin-top:8px; min-height:1.2em; font-size:0.92rem; }
</style></head><body><div class="card"><h1>Mobile Viewer PIN</h1><p>Enter the shop LAN viewer PIN to access reports on this device.</p><form method="post"><input type="password" name="pin" placeholder="Enter viewer PIN" autofocus><button type="submit">Open Viewer</button></form><div class="err">{{ error or '' }}</div><div class="hint">{{ hint or '' }}</div></div></body></html>""".replace("__APP_TITLE__", app_name)

    def _client_ip() -> str:
        forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return forwarded or request.remote_addr or "unknown"

    def _read_lan_attempt_state(ip: str) -> dict:
        entry = lan_attempts.get(ip, {"attempts": [], "locked_until": 0.0})
        now = time.time()
        attempts = [ts for ts in entry.get("attempts", []) if now - ts <= window_seconds]
        locked_until = float(entry.get("locked_until", 0.0) or 0.0)
        if locked_until and locked_until <= now:
            locked_until = 0.0
        clean = {"attempts": attempts, "locked_until": locked_until}
        if attempts or locked_until:
            lan_attempts[ip] = clean
        else:
            lan_attempts.pop(ip, None)
        return clean

    def _lan_lock_message(locked_until: float) -> str:
        remaining = max(1, int((locked_until - time.time()) // 60) + 1)
        return f"Too many failed PIN attempts. Try again in about {remaining} minute(s)."

    def _auth_ok():
        if not _lan_state.get("enabled", False):
            return False
        auth_at = float(session.get("lan_auth_at", 0.0) or 0.0)
        if not auth_at:
            return False
        age = time.time() - auth_at
        if age > int(_lan_state.get("session_minutes", 15)) * 60:
            session.clear()
            return False
        session["lan_auth_at"] = time.time()
        return True

    @app.before_request
    def _lan_guard():
        if request.endpoint in ("login", "static"):
            return None
        if not _lan_state.get("enabled", False):
            abort(503)
        if not _auth_ok():
            return redirect(url_for("login", next=request.path))
        return None

    @app.route("/")
    def index():
        return render_template_string(HTML)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not _lan_state.get("enabled", False):
            abort(503)
        error = ""
        hint = ""
        ip = _client_ip()
        state = _read_lan_attempt_state(ip)
        if state.get("locked_until", 0.0):
            msg = _lan_lock_message(state["locked_until"])
            return render_template_string(LOGIN_HTML, error=msg, hint=""), 429, {"Retry-After": str(lockout_seconds)}
        if request.method == "POST":
            entered = str(request.form.get("pin", "")).strip()
            if entered == _lan_state.get("pin", ""):
                lan_attempts.pop(ip, None)
                session["lan_auth_at"] = time.time()
                return redirect(request.args.get("next") or url_for("index"))
            attempts = state.get("attempts", [])
            attempts.append(time.time())
            if len(attempts) >= max_attempts:
                locked_until = time.time() + lockout_seconds
                lan_attempts[ip] = {"attempts": attempts, "locked_until": locked_until}
                msg = _lan_lock_message(locked_until)
                app_log(f"[lan viewer] lockout for {ip}")
                return render_template_string(LOGIN_HTML, error=msg, hint=""), 429, {"Retry-After": str(lockout_seconds)}
            lan_attempts[ip] = {"attempts": attempts, "locked_until": 0.0}
            remaining = max(0, max_attempts - len(attempts))
            error = "Invalid PIN."
            hint = f"{remaining} attempt(s) left before temporary lock."
        return render_template_string(LOGIN_HTML, error=error, hint=hint)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/api/summary")
    def summary():
        from datetime import date as d
        today = d.today().strftime("%Y-%m-%d")
        mo    = d.today().strftime("%Y-%m")
        td_rev = mo_rev = all_rev = 0.0
        td_bills = mo_bills = 0
        if os.path.exists(F_REPORT):
            with open(F_REPORT,"r",encoding="utf-8") as f:
                r   = csv.reader(f)
                hdr = next(r,None)
                ti  = 5 if (hdr and len(hdr)>=6) else 3
                for row in r:
                    if not row or len(row)<=ti: continue
                    v = float(row[ti]) if row[ti] else 0
                    all_rev += v
                    if row[0][:10]==today: td_rev+=v; td_bills+=1
                    if row[0][:7]==mo:    mo_rev+=v; mo_bills+=1
        return jsonify({"today_rev":round(td_rev,2),"today_bills":td_bills,
                         "month_rev":round(mo_rev,2),"all_rev":round(all_rev,2)})

    @app.route("/api/bills")
    def bills():
        rows = []
        if os.path.exists(F_REPORT):
            with open(F_REPORT,"r",encoding="utf-8") as f:
                r   = csv.reader(f)
                hdr = next(r,None)
                new = hdr and len(hdr)>=6
                for row in r:
                    if not row: continue
                    if new and len(row)>=6:
                        rows.append({"date":row[0],"invoice":row[1],
                                      "name":row[2],"phone":row[3],
                                      "payment":row[4],"total":row[5]})
                    elif len(row)>=4:
                        rows.append({"date":row[0],"invoice":"---",
                                      "name":row[1],"phone":row[2],
                                      "payment":"---","total":row[3]})
        return jsonify(list(reversed(rows)))

    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "localhost"
    _lan_state["ip"] = ip

    def run():
        # H3 FIX: Use the configured host (127.0.0.1 by default, 0.0.0.0 only
        # when allow_network_access is explicitly enabled).
        app.run(host=lan_host, port=port, debug=False, use_reloader=False)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    _lan_server = t
    _lan_state["thread"] = t
    return ip, None


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
#  CLOUD SYNC FRAME
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
class CloudSyncFrame(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])
        self.app = app
        self._register_cloud_sync_context_menu_callbacks()
        self._build()

    def _rbac_denied(self) -> bool:
        if self.app.has_permission("manage_cloud_sync"):
            return False
        messagebox.showerror("Access Denied",
                             "Cloud Sync settings are restricted for your role.")
        return True

    def _build(self):
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        left = tk.Frame(hdr, bg=C["card"])
        left.pack(side=tk.LEFT, padx=20)
        tk.Label(left, text="Cloud Sync & Mobile Access",
                 font=("Arial",15,"bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left, text="Manage folder sync, mobile viewer access, and offline backup from one workspace.",
                 font=("Arial",10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")

        intro = tk.Frame(self, bg=C["card"], padx=16, pady=12)
        intro.pack(fill=tk.X, padx=15, pady=(8, 8))
        tk.Label(intro, text="Cloud Sync Workspace",
                 font=("Arial",11,"bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(intro,
                 text="Keep billing data synced to a folder, expose a mobile viewer on local WiFi, and maintain an offline backup path.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial",10), justify="left").pack(anchor="w", pady=(4, 0))

        try:
            from salon_settings import feature_enabled as _feature_enabled
            mobile_viewer_enabled = _feature_enabled("mobile_viewer")
        except Exception:
            mobile_viewer_enabled = False

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        self._tab_icons = {}

        t1 = tk.Frame(nb, bg=C["bg"])
        t3 = tk.Frame(nb, bg=C["bg"])
        tabs = [
            ("folder_sync", t1, "Folder Sync (OneDrive/Dropbox)"),
            ("offline_backup", t3, "Offline Backup"),
        ]
        if mobile_viewer_enabled:
            t2 = tk.Frame(nb, bg=C["bg"])
            tabs.insert(1, ("mobile_viewer", t2, "Mobile Viewer (WiFi)"))

        for key, tab, text in tabs:
            icon = get_section_icon(key)
            if icon:
                self._tab_icons[key] = icon
                nb.add(tab, text=text, image=icon, compound="left")
            else:
                nb.add(tab, text=text)

        self._build_folder_sync(t1)
        if mobile_viewer_enabled:
            self._build_lan(t2)
        self._build_offline_backup(t3)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Folder Sync Tab Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build_folder_sync(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=30, pady=15)
        f.pack(fill=tk.BOTH, expand=True)
        self._quick_sync_buttons = []

        # How it works
        _lf1 = tk.Frame(f, bg=C["card"])
        _lf1.pack(fill=tk.X, pady=(0,16))
        _lf1h = tk.Frame(_lf1, bg=C["sidebar"], padx=12, pady=6)
        _lf1h.pack(fill=tk.X)
        tk.Label(_lf1h, text="How it works", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_lf1, bg=C["blue"], height=2).pack(fill=tk.X)
        info = tk.Frame(_lf1, bg=C["card"], padx=14, pady=10)
        info.pack(fill=tk.X)
        tk.Label(info,
                 text="- Install OneDrive / Dropbox / Google Drive desktop app\n"
                      "- Select that cloud folder below\n"
                      "- Data auto-copies to cloud on every bill save\n"
                      "- View files from any device via the cloud app\n"
                      "- Also works with USB drives, NAS, network folders",
                 bg=C["card"], fg=C["text"],
                 font=("Arial",12), justify="left").pack(anchor="w")

        svc_card = tk.Frame(f, bg=C["card"])
        svc_card.pack(fill=tk.X, pady=(0, 12))
        svc_hdr = tk.Frame(svc_card, bg=C["sidebar"], padx=12, pady=6)
        svc_hdr.pack(fill=tk.X)
        tk.Label(svc_hdr, text="Quick Select Cloud Service",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial",11,"bold")).pack(side=tk.LEFT)
        tk.Label(svc_hdr, text="Choose a common folder path or browse manually.",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial",9)).pack(side=tk.RIGHT)

        btn_row = tk.Frame(svc_card, bg=C["card"], padx=12, pady=10)
        btn_row.pack(fill=tk.X)

        for name, path in CLOUD_SUGGESTIONS.items():
            exists = os.path.exists(path)
            col = C["teal"] if exists else C["sidebar"]
            btn = ModernButton(btn_row, text=f"{'OK' if exists else 'X'}  {name}",
                               command=lambda p=path: self._set_folder(p),
                               color=col, hover_color=C["blue"],
                               width=160, height=30, radius=8,
                               font=("Arial", 9, "bold"),
                               )
            btn.pack(side=tk.LEFT, padx=(0,6))
            self._quick_sync_buttons.append({
                "name": name,
                "path": path,
                "exists": exists,
                "button": btn,
            })
        folder_card = tk.Frame(f, bg=C["card"])
        folder_card.pack(fill=tk.X, pady=(0, 12))
        folder_hdr = tk.Frame(folder_card, bg=C["sidebar"], padx=12, pady=6)
        folder_hdr.pack(fill=tk.X)
        tk.Label(folder_hdr, text="Sync Folder",
                 bg=C["sidebar"], fg=C["text"],
                 font=("Arial",11,"bold")).pack(side=tk.LEFT)
        tk.Label(folder_hdr, text="This location receives synced backup files and recent bills.",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial",9)).pack(side=tk.RIGHT)

        folder_row = tk.Frame(folder_card, bg=C["card"], padx=12, pady=10)
        folder_row.pack(fill=tk.X)

        cfg = get_sync_config()
        self.folder_var = tk.StringVar(value=cfg.get("folder",""))
        self.folder_lbl = tk.Label(folder_row,
                                    textvariable=self.folder_var,
                                    bg=C["input"], fg=C["lime"],
                                    font=("Arial",12), anchor="w",
                                    padx=8, pady=6)
        self.folder_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.folder_lbl.bind("<Button-3>", self._show_sync_folder_context_menu, add="+")
        self.folder_lbl.bind("<Shift-F10>", self._show_sync_folder_context_menu, add="+")
        browse_icon = get_action_icon("browse")
        clear_icon = get_action_icon("clear")
        sync_icon = get_action_icon("backup")
        ModernButton(folder_row, text="Browse", image=browse_icon, compound="left",
                     command=self._browse_folder,
                     color=C["blue"], hover_color="#154360",
                     width=100, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.LEFT, padx=(6,0))
        ModernButton(folder_row, text="Clear", image=clear_icon, compound="left",
                     command=self._clear_folder,
                     color=C["red"], hover_color="#c0392b",
                     width=90, height=30, radius=8,
                     font=("Arial", 10, "bold"),
                     ).pack(side=tk.LEFT, padx=(6,0))

        # Auto sync toggle
        self.auto_var = tk.BooleanVar(value=cfg.get("auto_sync",False))
        tk.Checkbutton(f,
                       text="Auto sync after every bill save",
                       variable=self.auto_var,
                       command=self._save_cfg,
                       bg=C["bg"], fg=C["text"],
                       selectcolor=C["input"],
                       font=("Arial",12),
                       cursor="hand2").pack(anchor="w", pady=(0,16))

        # Sync now button
        btn_row2 = tk.Frame(f, bg=C["bg"])
        btn_row2.pack(fill=tk.X)
        ModernButton(btn_row2, text="Sync Now", image=sync_icon, compound="left",
                     command=self._sync_now,
                     color=C["teal"], hover_color=C["blue"],
                     width=140, height=38, radius=8,
                     font=("Arial", 11, "bold"),
                     ).pack(side=tk.LEFT)

        self.last_lbl = tk.Label(btn_row2,
                                  text=f"Last sync: {cfg.get('last_sync','Never')}",
                                  bg=C["bg"], fg=C["muted"],
                                  font=("Arial",11))
        self.last_lbl.pack(side=tk.LEFT, padx=16)

        # Log
        tk.Label(f, text="Sync Log:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial",12,"bold")).pack(anchor="w", pady=(16,4))
        self.log_txt = tk.Text(f, height=7,
                                font=("Courier New",11),
                                bg=C["input"], fg=C["text"],
                                bd=0, state="disabled")
        self.log_txt.pack(fill=tk.X)
        self.log_txt.bind("<Button-3>", self._show_sync_log_context_menu, add="+")
        self.log_txt.bind("<Shift-F10>", self._show_sync_log_context_menu, add="+")
        self._refresh_quick_sync_buttons()

    def _set_folder(self, path: str):
        self.folder_var.set(path)
        self._save_cfg()
        self._refresh_quick_sync_buttons()

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Sync Folder")
        if folder:
            self.folder_var.set(folder)
            self._save_cfg()
            self._refresh_quick_sync_buttons()

    def _clear_folder(self):
        self.folder_var.set("")
        self.auto_var.set(False)
        self._save_cfg()
        self._refresh_quick_sync_buttons()

    def _save_cfg(self):
        if self._rbac_denied(): return
        cfg = get_sync_config()
        cfg["folder"]    = self.folder_var.get()
        cfg["auto_sync"] = self.auto_var.get()
        save_sync_config(cfg)
        self._refresh_quick_sync_buttons()

    def _refresh_quick_sync_buttons(self):
        current = os.path.normcase(os.path.normpath((self.folder_var.get() or "").strip()))
        for info in getattr(self, "_quick_sync_buttons", []):
            path = os.path.normcase(os.path.normpath(info["path"]))
            exists = bool(info["exists"])
            is_active = bool(current) and current == path
            prefix = "OK" if exists else "X"
            if is_active:
                prefix = "SELECTED"
            btn = info["button"]
            btn.set_text(f"{prefix}  {info['name']}")
            if is_active:
                btn.set_color(C["blue"], "#154360")
            elif exists:
                btn.set_color(C["teal"], C["blue"])
            else:
                btn.set_color(C["sidebar"], C["blue"])

    def _log(self, msg: str):
        self.log_txt.config(state="normal")
        self.log_txt.insert("end", f"{now_str()[:16]}  {msg}\n")
        self.log_txt.see("end")
        self.log_txt.config(state="disabled")

    def _sync_now(self):
        folder = self.folder_var.get()
        if not folder:
            messagebox.showerror("Error","Select a sync folder first."); return
        if not os.path.exists(folder):
            messagebox.showerror("Error",f"Folder not found:\n{folder}"); return

        self._save_cfg()
        self._log("Starting sync...")

        def _run():
            def progress(fname, status):
                icon = "OK" if status=="ok" else "ERR"
                self.after(0, lambda: self._log(f"  {icon} {fname}"))
            success, errors = sync_to_folder(folder, progress)
            dest = os.path.join(folder, get_backup_folder_name())
            msg  = f"Sync complete: {success} files -> {dest}"
            if errors:
                msg += f"\nWarnings: {len(errors)} errors"
            self.after(0, lambda: (
                self._log(msg),
                self.last_lbl.config(text=f"Last sync: {now_str()}"),
                messagebox.showinfo("Sync Complete",
                                     f"{success} files synced.\n\nLocation:\n{dest}")))

        threading.Thread(target=_run, daemon=True).start()

    # -- Offline Backup Tab -------------------------------------------------
    def _build_offline_backup(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=30, pady=15)
        f.pack(fill=tk.BOTH, expand=True)
        browse_icon = get_action_icon("browse")

        info_card = tk.Frame(f, bg=C["card"])
        info_card.pack(fill=tk.X, pady=(0, 16))
        info_hdr = tk.Frame(info_card, bg=C["sidebar"], padx=12, pady=6)
        info_hdr.pack(fill=tk.X)
        tk.Label(info_hdr, text="Offline Backup and Restore",
                 font=("Arial", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(info_card, bg=C["gold"], height=2).pack(fill=tk.X)
        info = tk.Frame(info_card, bg=C["card"], padx=14, pady=10)
        info.pack(fill=tk.X)
        tk.Label(
            info,
            text="Use another drive, USB disk, or external folder as a live offline backup.\n"
                 "The app can update this backup after every billing save and restore data from it later.",
            bg=C["card"], fg=C["text"], font=("Arial", 12), justify="left"
        ).pack(anchor="w")

        cfg = get_backup_config()
        self.offline_folder_var = tk.StringVar(value=normalize_backup_folder(cfg.get("folder", "")))
        self.offline_auto_var = tk.BooleanVar(value=cfg.get("auto_backup", False))

        tk.Label(f, text="Offline Backup Folder:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 4))

        row = tk.Frame(f, bg=C["bg"])
        row.pack(fill=tk.X, pady=(0, 10))
        self.offline_folder_lbl = tk.Label(
            row,
            textvariable=self.offline_folder_var,
            bg=C["input"],
            fg=C["lime"],
            font=("Arial", 12),
            anchor="w",
            padx=8,
            pady=6,
        )
        self.offline_folder_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.offline_folder_lbl.bind("<Button-3>", self._show_offline_backup_context_menu, add="+")
        self.offline_folder_lbl.bind("<Shift-F10>", self._show_offline_backup_context_menu, add="+")
        backup_icon = get_action_icon("backup")
        restore_icon = get_action_icon("restore")
        clear_icon = get_action_icon("clear")

        ModernButton(row, text="Browse", image=browse_icon, compound="left",
                     command=self._browse_offline_folder,
                     color=C["blue"], hover_color="#154360",
                     width=100, height=30, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(6, 0))
        ModernButton(row, text="Clear", image=clear_icon, compound="left",
                     command=self._clear_offline_folder,
                     color=C["red"], hover_color="#c0392b",
                     width=90, height=30, radius=8,
                     font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(6, 0))

        self.offline_dest_lbl = tk.Label(
            f,
            text="Backup destination: -",
            bg=C["bg"], fg=C["muted"],
            font=("Arial", 10)
        )
        self.offline_dest_lbl.pack(anchor="w", pady=(0, 10))

        tk.Checkbutton(
            f,
            text="Auto update offline backup after every bill save",
            variable=self.offline_auto_var,
            command=self._save_offline_cfg,
            bg=C["bg"], fg=C["text"],
            selectcolor=C["input"],
            font=("Arial", 12),
            cursor="hand2"
        ).pack(anchor="w", pady=(0, 14))

        btns = tk.Frame(f, bg=C["bg"])
        btns.pack(fill=tk.X, pady=(0, 12))
        ModernButton(btns, text="Backup Now", image=backup_icon, compound="left",
                     command=self._offline_backup_now,
                     color=C["teal"], hover_color=C["blue"],
                     width=140, height=36, radius=8,
                     font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        ModernButton(btns, text="Restore From Backup", image=restore_icon, compound="left",
                     command=self._restore_offline_backup,
                     color=C["orange"], hover_color="#b35f18",
                     width=180, height=36, radius=8,
                     font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(8, 0))

        self.offline_status_lbl = tk.Label(
            f,
            text=f"Last backup: {cfg.get('last_backup', 'Never')}    Last restore: {cfg.get('last_restore', 'Never')}",
            bg=C["bg"], fg=C["muted"], font=("Arial", 11)
        )
        self.offline_status_lbl.pack(anchor="w", pady=(0, 12))

        tk.Label(f, text="Backup Log:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 4))
        self.offline_log_txt = tk.Text(
            f, height=8, font=("Courier New", 11),
            bg=C["input"], fg=C["text"], bd=0, state="disabled"
        )
        self.offline_log_txt.pack(fill=tk.BOTH, expand=True)
        self.offline_log_txt.bind("<Button-3>", self._show_offline_log_context_menu, add="+")
        self.offline_log_txt.bind("<Shift-F10>", self._show_offline_log_context_menu, add="+")
        self._refresh_offline_status()

    def _browse_offline_folder(self):
        folder = filedialog.askdirectory(title="Select Offline Backup Folder")
        if folder:
            self.offline_folder_var.set(normalize_backup_folder(folder))
            self._save_offline_cfg()

    def _clear_offline_folder(self):
        self.offline_folder_var.set("")
        self.offline_auto_var.set(False)
        self._save_offline_cfg()

    def _save_offline_cfg(self):
        cfg = get_backup_config()
        clean_folder = normalize_backup_folder(self.offline_folder_var.get())
        self.offline_folder_var.set(clean_folder)
        cfg["folder"] = clean_folder
        cfg["auto_backup"] = bool(self.offline_auto_var.get())
        save_backup_config(cfg)
        self._refresh_offline_status()

    def _offline_log(self, msg: str):
        self.offline_log_txt.config(state="normal")
        self.offline_log_txt.insert("end", f"{now_str()}  {msg}\n")
        self.offline_log_txt.see("end")
        self.offline_log_txt.config(state="disabled")

    def _refresh_offline_status(self):
        cfg = get_backup_config()
        dest = backup_destination(cfg.get("folder", ""))
        self.offline_dest_lbl.config(
            text=f"Backup destination: {dest}" if dest else "Backup destination: -"
        )
        self.offline_status_lbl.config(
            text=f"Last backup: {cfg.get('last_backup', 'Never')}    Last restore: {cfg.get('last_restore', 'Never')}"
        )

    def _offline_backup_now(self):
        folder = self.offline_folder_var.get().strip()
        if not folder:
            messagebox.showerror("Offline Backup", "Select a backup folder first.")
            return
        self._save_offline_cfg()
        self._offline_log("Starting offline backup...")

        def _run():
            def progress(name, status):
                icon = "OK" if status == "ok" else "ERR"
                self.after(0, lambda: self._offline_log(f"{icon} {name}"))
            success, errors, root = sync_offline_backup(folder, progress)
            self.after(0, self._refresh_offline_status)
            if errors:
                self.after(0, lambda: messagebox.showwarning(
                    "Offline Backup",
                    f"Backed up {success} files to:\n{root}\n\nWarnings:\n" + "\n".join(errors[:8])
                ))
            else:
                self.after(0, lambda: messagebox.showinfo(
                    "Offline Backup",
                    f"Backup complete.\n\nFiles copied: {success}\nLocation:\n{root}"
                ))

        threading.Thread(target=_run, daemon=True).start()

    def _restore_offline_backup(self):
        folder = filedialog.askdirectory(title="Select Offline Backup Folder")
        if not folder:
            return
        if not messagebox.askyesno(
            "Restore Offline Backup",
            "This will import data from the selected backup folder into the current system.\n\nContinue?"
        ):
            return
        self._offline_log("Starting restore from offline backup...")

        def _run():
            def progress(name, status):
                icon = "OK" if status == "ok" else "ERR"
                self.after(0, lambda: self._offline_log(f"{icon} {name}"))
            restored, errors = restore_from_backup(folder, progress)
            self.after(0, self._refresh_offline_status)
            if errors:
                self.after(0, lambda: messagebox.showwarning(
                    "Restore Completed with Warnings",
                    f"Restored {restored} items.\n\nWarnings:\n" + "\n".join(errors[:8])
                ))
            else:
                self.after(0, lambda: messagebox.showinfo(
                    "Restore Completed",
                    f"Restored {restored} items.\nPlease restart the app to reload all restored data."
                ))

        threading.Thread(target=_run, daemon=True).start()

    # Ã¢â€â‚¬Ã¢â€â‚¬ LAN Viewer Tab Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build_lan(self, parent):
        f = tk.Frame(parent, bg=C["bg"], padx=30, pady=20)
        f.pack(fill=tk.BOTH, expand=True)

        _lf2 = tk.Frame(f, bg=C["card"])
        _lf2.pack(fill=tk.X, pady=(0,20))
        _lf2h = tk.Frame(_lf2, bg=C["sidebar"], padx=12, pady=6)
        _lf2h.pack(fill=tk.X)
        tk.Label(_lf2h, text="Mobile Web Viewer", font=("Arial",11,"bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Frame(_lf2, bg=C["teal"], height=2).pack(fill=tk.X)
        info = tk.Frame(_lf2, bg=C["card"], padx=14, pady=10)
        info.pack(fill=tk.X)
        tk.Label(info,
                 text="View reports and bills from your mobile browser\n"
                      "No internet needed - works on same WiFi\n"
                      "Mobile, tablet, laptop - any device\n"
                      "Live updates every 30 seconds\n"
                      "Install Flask once: pip install flask",
                 bg=C["card"], fg=C["text"],
                 font=("Arial",12), justify="left").pack(anchor="w")

        # Port setting
        port_row = tk.Frame(f, bg=C["bg"])
        port_row.pack(fill=tk.X, pady=(0,16))
        tk.Label(port_row, text="Port:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial",11,"bold")).pack(side=tk.LEFT, padx=(0,8))
        self.port_var = tk.StringVar(value=str(get_sync_config().get("lan_port",5050)))
        tk.Entry(port_row, textvariable=self.port_var,
                 font=("Arial",11), bg=C["input"],
                 fg=C["text"], bd=0, width=8,
                 insertbackground=C["accent"]).pack(side=tk.LEFT, ipady=5)
        tk.Label(port_row, text="(default: 5050)",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial",11)).pack(side=tk.LEFT, padx=8)
        cfg = get_sync_config()
        pin_row = tk.Frame(f, bg=C["bg"])
        pin_row.pack(fill=tk.X, pady=(0,16))
        tk.Label(pin_row, text="Viewer PIN:",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial",11,"bold")).pack(side=tk.LEFT, padx=(0,8))
        self.lan_pin_var = tk.StringVar(value=str(cfg.get("lan_pin", "")))
        tk.Entry(pin_row, textvariable=self.lan_pin_var,
                 show="*", font=("Arial",11), bg=C["input"],
                 fg=C["text"], bd=0, width=14,
                 insertbackground=C["accent"]).pack(side=tk.LEFT, ipady=5)
        tk.Label(pin_row, text="Session (min):",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial",11,"bold")).pack(side=tk.LEFT, padx=(18,8))
        self.lan_session_var = tk.StringVar(value=str(cfg.get("lan_session_minutes", 15)))
        tk.Entry(pin_row, textvariable=self.lan_session_var,
                 font=("Arial",11), bg=C["input"],
                 fg=C["text"], bd=0, width=6,
                 insertbackground=C["accent"]).pack(side=tk.LEFT, ipady=5)

        # Start/Stop button
        mobile_icon = get_section_icon("mobile_viewer")
        self.lan_btn = ModernButton(f, text="Start Mobile Viewer", image=mobile_icon, compound="left",
                                    command=self._toggle_lan,
                                    color=C["teal"], hover_color=C["blue"],
                                    width=200, height=38, radius=8,
                                    font=("Arial", 11, "bold"))
        self.lan_btn.pack(anchor="w", pady=(0,16))

        # URL display
        self.url_f = tk.Frame(f, bg=C["card"], padx=16, pady=12)
        self.url_f.pack(fill=tk.X)
        self.url_lbl = tk.Label(self.url_f,
                                 text="Start the viewer to get the mobile URL",
                                 bg=C["card"], fg=C["muted"],
                                 font=("Arial",12))
        self.url_lbl.pack()
        self.url_lbl.bind("<Button-3>", self._show_lan_context_menu, add="+")
        self.url_lbl.bind("<Shift-F10>", self._show_lan_context_menu, add="+")

        self.qr_lbl = tk.Label(self.url_f, text="",
                                bg=C["card"], fg=C["gold"],
                                font=("Arial",11))
        self.qr_lbl.pack(pady=(6,0))

        self.lan_diag_lbl = tk.Label(
            self.url_f,
            text="",
            bg=C["card"], fg=C["muted"],
            font=("Arial",10), justify="center"
        )
        self.lan_diag_lbl.pack(pady=(6, 0))

        diag_row = tk.Frame(f, bg=C["bg"])
        diag_row.pack(fill=tk.X, pady=(12, 0))
        ModernButton(diag_row, text="Run Connection Check",
                     command=self._run_lan_diagnostics,
                     color=C["blue"], hover_color="#154360",
                     width=170, height=32, radius=8,
                     font=("Arial",10,"bold")).pack(side=tk.LEFT)

        self._lan_running = False

    def _toggle_lan(self):
        if self._lan_running:
            self._lan_running = False
            _lan_state["enabled"] = False
            self.lan_btn.set_text("Start Mobile Viewer") or self.lan_btn.set_color(C["teal"], C["blue"])
            self.url_lbl.config(text="Server stopped.", fg=C["muted"])
            self.qr_lbl.config(text="")
            self.lan_diag_lbl.config(text="")
            return

        port = int(self.port_var.get() or "5050")
        pin = str(self.lan_pin_var.get() or "").strip()
        session_minutes = int(self.lan_session_var.get() or "15")
        if len(pin) < 4:
            messagebox.showwarning("Mobile Viewer", "Enter a Viewer PIN with at least 4 digits.")
            return
        cfg  = get_sync_config()
        cfg["lan_port"] = port
        cfg["lan_pin"] = pin
        cfg["lan_session_minutes"] = session_minutes
        save_sync_config(cfg)

        self.url_lbl.config(text="Starting server...", fg=C["muted"])
        self.lan_diag_lbl.config(text="")
        self.lan_btn.set_text("Starting...")
        self.lan_btn.set_color(C.get("sidebar", C["card"]), C.get("sidebar", C["card"]))

        def _start():
            ip, err = start_lan_server(port, pin=pin, session_minutes=session_minutes)
            if err:
                self.after(0, lambda: (
                    messagebox.showerror("Error",
                                          f"Could not start server:\n{err}\n\n"
                                          "Run: pip install flask"),
                    self.lan_btn.set_text("Start Mobile Viewer"),
                    self.lan_btn.set_color(C["teal"], C["blue"])))
                return

            url = f"http://{ip}:{port}"
            self._lan_running = True
            self.after(0, lambda: (
                self.lan_btn.set_text("Stop Viewer") or self.lan_btn.set_color(C["red"], "#c0392b"),
                self.url_lbl.config(
                    text=url,
                    fg=C["lime"],
                    font=("Arial",14,"bold"),
                    cursor="hand2"),
                self.qr_lbl.config(
                    text="Open this URL in your mobile browser (same WiFi)\n"
                         "Enter the Viewer PIN to continue."),
                self.lan_diag_lbl.config(
                    text="If mobile does not open the login page, run Connection Check.\n"
                         "Most common causes: Windows Firewall or phone not on the same WiFi.",
                    fg=C["muted"]),
            ))

        threading.Thread(target=_start, daemon=True).start()

    def _run_lan_diagnostics(self):
        if not self._lan_running:
            messagebox.showinfo(
                "Mobile Viewer",
                "Start the Mobile Viewer first, then run the connection check."
            )
            return

        port = int(self.port_var.get() or "5050")
        local_url = f"http://127.0.0.1:{port}/"

        def _check():
            try:
                with urllib.request.urlopen(local_url, timeout=3) as res:
                    ok = 200 <= getattr(res, "status", 200) < 400
            except Exception:
                ok = False

            if ok:
                self.after(0, lambda: self.lan_diag_lbl.config(
                    text="Viewer is running on this PC. If mobile still fails,\n"
                         "allow Python in Windows Firewall and confirm both devices use the same WiFi.",
                    fg=C["gold"]
                ))
            else:
                self.after(0, lambda: self.lan_diag_lbl.config(
                    text="Local self-test failed. Stop and start the viewer again,\n"
                         "or change the port and retry.",
                    fg=C["red"]
                ))

        threading.Thread(target=_check, daemon=True).start()

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

    def _show_sync_folder_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.cloud_sync_context_menu import get_sync_folder_sections

            folder_path = self.folder_var.get().strip() if hasattr(self, "folder_var") else ""
            context = build_context(
                "cloud_sync",
                entity_type="folder_sync",
                selected_row={"folder_path": folder_path},
                selected_text=folder_path,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.ENTRY,
                widget_id="cloud_sync_folder",
                extra={"has_sync_folder": bool(folder_path)},
            )
            menu = renderer_service.build_menu(self, get_sync_folder_sections(), context)
            return self._popup_context_menu(event, menu, self.folder_lbl)
        except Exception as exc:
            app_log(f"[cloud sync folder context menu] {exc}")
            return "break"

    def _show_sync_log_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.cloud_sync_context_menu import get_sync_log_sections

            context = build_context(
                "cloud_sync",
                entity_type="sync_log",
                selected_text="",
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TEXT,
                widget_id="cloud_sync_log",
            )
            menu = renderer_service.build_menu(self, get_sync_log_sections(), context)
            return self._popup_context_menu(event, menu, self.log_txt)
        except Exception as exc:
            app_log(f"[cloud sync log context menu] {exc}")
            return "break"

    def _show_offline_backup_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.cloud_sync_context_menu import get_offline_backup_sections

            folder_path = self.offline_folder_var.get().strip() if hasattr(self, "offline_folder_var") else ""
            context = build_context(
                "cloud_sync",
                entity_type="offline_backup",
                selected_row={"folder_path": folder_path},
                selected_text=folder_path,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.ENTRY,
                widget_id="cloud_sync_offline_folder",
                extra={"has_offline_folder": bool(folder_path)},
            )
            menu = renderer_service.build_menu(self, get_offline_backup_sections(), context)
            return self._popup_context_menu(event, menu, self.offline_folder_lbl)
        except Exception as exc:
            app_log(f"[cloud sync offline context menu] {exc}")
            return "break"

    def _show_offline_log_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.cloud_sync_context_menu import get_offline_log_sections

            context = build_context(
                "cloud_sync",
                entity_type="offline_log",
                selected_text="",
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.TEXT,
                widget_id="cloud_sync_offline_log",
            )
            menu = renderer_service.build_menu(self, get_offline_log_sections(), context)
            return self._popup_context_menu(event, menu, self.offline_log_txt)
        except Exception as exc:
            app_log(f"[cloud sync offline log context menu] {exc}")
            return "break"

    def _show_lan_context_menu(self, event):
        try:
            from shared.context_menu.constants import WidgetType
            from shared.context_menu.menu_context_factory import build_context
            from shared.context_menu.renderer import renderer_service
            from shared.context_menu_definitions.cloud_sync_context_menu import get_lan_sections

            url = self.url_lbl.cget("text").strip() if hasattr(self, "url_lbl") else ""
            context = build_context(
                "cloud_sync",
                entity_type="mobile_viewer",
                selected_row={"viewer_url": url},
                selected_text=url,
                user_role=self.app.current_user.get("role", "") if getattr(self.app, "current_user", None) else "",
                widget_type=WidgetType.CARD,
                widget_id="cloud_sync_lan_url",
                extra={"has_viewer_url": url.startswith("http")},
            )
            menu = renderer_service.build_menu(self, get_lan_sections(), context)
            return self._popup_context_menu(event, menu, self.url_lbl)
        except Exception as exc:
            app_log(f"[cloud sync lan context menu] {exc}")
            return "break"

    def _copy_text_widget_selection(self, widget) -> bool:
        from shared.context_menu.clipboard_service import clipboard_service

        return clipboard_service.copy_selection(widget)

    def _copy_text_widget_all(self, widget) -> bool:
        from shared.context_menu.clipboard_service import clipboard_service

        return clipboard_service.copy_all(widget)

    def _select_all_text_widget(self, widget) -> bool:
        from shared.context_menu.clipboard_service import clipboard_service

        return clipboard_service.select_all(widget)

    def _register_cloud_sync_context_menu_callbacks(self):
        from shared.context_menu.action_adapter import action_adapter
        from shared.context_menu.clipboard_service import clipboard_service
        from shared.context_menu_definitions.cloud_sync_context_menu import CloudSyncContextAction

        action_adapter.register(
            CloudSyncContextAction.COPY_SYNC_FOLDER,
            lambda _ctx, _act: clipboard_service.copy_text(self, self.folder_var.get().strip() if hasattr(self, "folder_var") else ""),
        )
        action_adapter.register(CloudSyncContextAction.SYNC_NOW, lambda _ctx, _act: self._sync_now())
        action_adapter.register(CloudSyncContextAction.REFRESH_SYNC, lambda _ctx, _act: self.refresh())
        action_adapter.register(
            CloudSyncContextAction.COPY_SYNC_LOG_SELECTION,
            lambda _ctx, _act: self._copy_text_widget_selection(self.log_txt),
        )
        action_adapter.register(
            CloudSyncContextAction.COPY_SYNC_LOG_ALL,
            lambda _ctx, _act: self._copy_text_widget_all(self.log_txt),
        )
        action_adapter.register(
            CloudSyncContextAction.SELECT_SYNC_LOG_ALL,
            lambda _ctx, _act: self._select_all_text_widget(self.log_txt),
        )
        action_adapter.register(
            CloudSyncContextAction.COPY_OFFLINE_FOLDER,
            lambda _ctx, _act: clipboard_service.copy_text(self, self.offline_folder_var.get().strip() if hasattr(self, "offline_folder_var") else ""),
        )
        action_adapter.register(CloudSyncContextAction.BACKUP_NOW, lambda _ctx, _act: self._offline_backup_now())
        action_adapter.register(CloudSyncContextAction.REFRESH_OFFLINE, lambda _ctx, _act: self._refresh_offline_status())
        action_adapter.register(
            CloudSyncContextAction.COPY_OFFLINE_LOG_SELECTION,
            lambda _ctx, _act: self._copy_text_widget_selection(self.offline_log_txt),
        )
        action_adapter.register(
            CloudSyncContextAction.COPY_OFFLINE_LOG_ALL,
            lambda _ctx, _act: self._copy_text_widget_all(self.offline_log_txt),
        )
        action_adapter.register(
            CloudSyncContextAction.SELECT_OFFLINE_LOG_ALL,
            lambda _ctx, _act: self._select_all_text_widget(self.offline_log_txt),
        )
        action_adapter.register(
            CloudSyncContextAction.COPY_VIEWER_URL,
            lambda _ctx, _act: clipboard_service.copy_text(self, self.url_lbl.cget("text").strip() if hasattr(self, "url_lbl") else ""),
        )
        action_adapter.register(CloudSyncContextAction.RUN_CONNECTION_CHECK, lambda _ctx, _act: self._run_lan_diagnostics())

    def refresh(self):
        cfg = get_sync_config()
        if hasattr(self, "folder_var"):
            self.folder_var.set(cfg.get("folder", ""))
        if hasattr(self, "auto_var"):
            self.auto_var.set(cfg.get("auto_sync", False))
        if hasattr(self, "last_lbl"):
            self.last_lbl.config(text=f"Last sync: {cfg.get('last_sync', 'Never')}")
        if hasattr(self, "_refresh_quick_sync_buttons"):
            self._refresh_quick_sync_buttons()
        if hasattr(self, "port_var"):
            self.port_var.set(str(cfg.get("lan_port", 5050)))
        if hasattr(self, "lan_pin_var"):
            self.lan_pin_var.set(str(cfg.get("lan_pin", "")))
        if hasattr(self, "lan_session_var"):
            self.lan_session_var.set(str(cfg.get("lan_session_minutes", 15)))
        backup_cfg = get_backup_config()
        if hasattr(self, "offline_folder_var"):
            self.offline_folder_var.set(normalize_backup_folder(backup_cfg.get("folder", "")))
        if hasattr(self, "offline_auto_var"):
            self.offline_auto_var.set(bool(backup_cfg.get("auto_backup", False)))
        if hasattr(self, "_refresh_offline_status"):
            self._refresh_offline_status()
