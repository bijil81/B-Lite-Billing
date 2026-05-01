import tkinter as tk


def render_security_tab(settings_frame):
    from salon_settings import C, ModernButton, get_action_icon, get_settings

    cfg = get_settings()
    body = settings_frame._scroll("sec")
    settings_frame._show_security_passwords = tk.BooleanVar(value=False)

    password_sec = settings_frame._sec(body, "\U0001f511  Change Password", C["red"])
    settings_frame._pw_curr = settings_frame._pw_entry(password_sec, "Current Password:")
    settings_frame._pw_new = settings_frame._pw_entry(password_sec, "New Password:")
    settings_frame._pw_conf = settings_frame._pw_entry(password_sec, "Confirm New Password:")
    tk.Checkbutton(
        password_sec,
        text="Show Passwords",
        variable=settings_frame._show_security_passwords,
        command=settings_frame._toggle_security_passwords,
        bg=C["bg"],
        fg=C["muted"],
        selectcolor=C["input"],
        font=("Arial", 10),
    ).pack(anchor="w", pady=(0, 8))
    ModernButton(
        password_sec,
        text="Change Password",
        image=get_action_icon("save"),
        compound="left",
        command=settings_frame._change_pw,
        color=C["red"],
        hover_color="#c0392b",
        width=200,
        height=36,
        radius=8,
        font=("Arial", 11, "bold"),
    ).pack(anchor="w", pady=(4, 0))

    login_sec = settings_frame._sec(body, "\U0001f512  Login Security")
    settings_frame._auto_logout = tk.BooleanVar(value=cfg.get("auto_logout", False))
    settings_frame._req_pw_del = tk.BooleanVar(value=cfg.get("require_pw_bill", False))
    settings_frame._chk(login_sec, "Auto logout after 30 min inactivity", settings_frame._auto_logout)
    settings_frame._chk(login_sec, "Require password to delete bills/data", settings_frame._req_pw_del)

    settings_frame._savebtn(body, "\U0001f4be  Save Security", settings_frame._save_security)

