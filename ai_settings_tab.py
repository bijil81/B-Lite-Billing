import tkinter as tk
from tkinter import ttk


def render_ai_settings_tab(settings_frame):
    from salon_settings import C, KEYRING_AVAILABLE, get_settings, load_ai_api_key

    try:
        settings_frame._tabs["ai"]
    except KeyError:
        return

    ai_cfg = get_settings().get("ai_config", {})
    stored_ai_key = load_ai_api_key(ai_cfg)
    body = settings_frame._scroll("ai")

    sec1 = settings_frame._sec(body, "\U0001f916  AI Assistant", C["accent"])
    settings_frame._ai_enabled = tk.BooleanVar(value=ai_cfg.get("enabled", True))
    tk.Checkbutton(sec1, text="Enable AI Assistant", variable=settings_frame._ai_enabled, bg=C["card"], fg=C["text"], selectcolor=C["input"], font=("Arial", 12), cursor="hand2").pack(anchor="w", pady=(0, 10))

    tk.Label(sec1, text="Anthropic API Key:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
    key_row = tk.Frame(sec1, bg=C["card"])
    key_row.pack(fill=tk.X, pady=(4, 2))
    settings_frame._ai_key_var = tk.StringVar(value=stored_ai_key)
    settings_frame._ai_key_ent = tk.Entry(key_row, textvariable=settings_frame._ai_key_var, show="*", font=("Arial", 11), bg=C["input"], fg=C["text"], bd=0, insertbackground=C["accent"])
    settings_frame._ai_key_ent.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)

    show_var = tk.BooleanVar(value=False)
    tk.Checkbutton(key_row, text="Show", variable=show_var, command=lambda: settings_frame._ai_key_ent.configure(show="" if show_var.get() else "*"), bg=C["card"], fg=C["muted"], selectcolor=C["input"], font=("Arial", 10)).pack(side=tk.LEFT, padx=8)

    tk.Label(sec1, text="Get free key: console.anthropic.com/settings/keys", bg=C["card"], fg=C["muted"], font=("Arial", 10)).pack(anchor="w", pady=(2, 10))
    storage_hint = "Stored securely using Windows Credential Manager" if KEYRING_AVAILABLE else "Secure keyring not available. API keys cannot be stored until Windows Credential Manager support is available."
    tk.Label(sec1, text=storage_hint, bg=C["card"], fg=C["muted"], font=("Arial", 9)).pack(anchor="w", pady=(0, 10))

    tk.Label(sec1, text="Model:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
    settings_frame._ai_model_var = tk.StringVar(value=ai_cfg.get("model", "claude-sonnet-4-5"))
    ttk.Combobox(sec1, textvariable=settings_frame._ai_model_var, values=["claude-sonnet-4-5", "claude-haiku-4-5-20251001", "claude-opus-4-6"], state="readonly", font=("Arial", 11), width=30).pack(anchor="w", pady=(4, 14))

    settings_frame._savebtn(body, "\U0001f4be  Save AI Settings", settings_frame._save_ai)

    sec2 = settings_frame._sec(body, "\U0001f4ca  Status", C["teal"])
    settings_frame._ai_status_lbl = tk.Label(sec2, text="", bg=C["card"], fg=C["muted"], font=("Arial", 11))
    settings_frame._ai_status_lbl.pack(anchor="w")
    settings_frame._refresh_ai_status()

    sec3 = settings_frame._sec(body, "\U0001f4a1  How to Use", C["blue"])
    tk.Label(sec3, text=("Ask the AI assistant anything about your shop:\n\n"
                         "  '\u2022 Today sales ethra?'       real revenue data\n"
                         "  '\u2022 Low stock items?'         inventory alerts\n"
                         "  '\u2022 Customer Ammu details'    visit history\n"
                         "  '\u2022 Create bill: Haircut 200' open billing\n"
                         "  '\u2022 Today appointments?'      schedule view\n"
                         "  '\u2022 Staff summary'            attendance + commission\n\n"
                         "Click \U0001f916 floating button (bottom-right)\n"
                         "or open the AI Assistant tab from the sidebar."),
             bg=C["card"], fg=C["text"], font=("Arial", 10), justify="left").pack(anchor="w")
