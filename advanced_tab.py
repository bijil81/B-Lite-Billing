import tkinter as tk
from tkinter import ttk


def render_advanced_tab(settings_frame):
    from salon_settings import C, ModernButton, feature_enabled, get_settings, load_multibranch_api_key, load_whatsapp_provider_secret

    cfg = get_settings()
    body = settings_frame._scroll("advanced")

    feature_sec = settings_frame._sec(body, "Optional Premium Features", C["purple"])
    tk.Label(feature_sec, text="Enable advanced features only when the customer needs them. Disabled features stay hidden.", bg=C["card"], fg=C["muted"], justify="left", font=("Arial", 10)).pack(anchor="w", pady=(0, 10))

    settings_frame._feature_ai = tk.BooleanVar(value=feature_enabled("ai_assistant", cfg))
    settings_frame._feature_mobile = tk.BooleanVar(value=feature_enabled("mobile_viewer", cfg))
    settings_frame._feature_wa_api = tk.BooleanVar(value=feature_enabled("whatsapp_api", cfg))
    settings_frame._feature_multibranch = tk.BooleanVar(value=feature_enabled("multibranch", cfg))

    settings_frame._chk(feature_sec, "Enable AI Assistant module", settings_frame._feature_ai)
    settings_frame._chk(feature_sec, "Enable Mobile Viewer inside Cloud Sync", settings_frame._feature_mobile)
    settings_frame._chk(feature_sec, "Enable WhatsApp API provider support", settings_frame._feature_wa_api)
    settings_frame._chk(feature_sec, "Enable Multi-Branch sync foundation", settings_frame._feature_multibranch)

    settings_frame._feature_status_grid(feature_sec, [
        {"label": "AI Assistant", "state": "ON" if settings_frame._feature_ai.get() else "OFF", "caption": "Sidebar tab and floating AI tools.", "color": C["green"] if settings_frame._feature_ai.get() else C["muted"]},
        {"label": "Mobile Viewer", "state": "ON" if settings_frame._feature_mobile.get() else "OFF", "caption": "Optional tab inside Cloud Sync only.", "color": C["green"] if settings_frame._feature_mobile.get() else C["muted"]},
        {"label": "Premium APIs", "state": "READY" if (settings_frame._feature_wa_api.get() or settings_frame._feature_multibranch.get()) else "OFF", "caption": "Customer-funded optional integrations.", "color": C["gold"] if (settings_frame._feature_wa_api.get() or settings_frame._feature_multibranch.get()) else C["muted"]},
    ])

    wa_cfg = cfg.get("whatsapp_api_config", {})
    wa_sec = settings_frame._sec(body, "WhatsApp API Providers", C["teal"])
    tk.Label(wa_sec, text="Optional paid integration. Customer must buy and maintain their own provider account.", bg=C["card"], fg=C["muted"], justify="left", font=("Arial", 10)).pack(anchor="w", pady=(0, 8))
    settings_frame._wa_api_enabled = tk.BooleanVar(value=wa_cfg.get("enabled", False))
    settings_frame._wa_api_fallback = tk.BooleanVar(value=wa_cfg.get("fallback_to_selenium", True))
    settings_frame._chk(wa_sec, "Enable API mode for configured provider", settings_frame._wa_api_enabled)
    settings_frame._chk(wa_sec, "Fallback to current Selenium WhatsApp mode", settings_frame._wa_api_fallback)

    settings_frame._wa_provider = tk.StringVar(value=wa_cfg.get("provider", "meta"))
    tk.Label(wa_sec, text="Provider:", bg=C["card"], fg=C["muted"], font=("Arial", 11, "bold")).pack(anchor="w")
    ttk.Combobox(wa_sec, textvariable=settings_frame._wa_provider, values=["meta", "gupshup", "twilio"], state="readonly", font=("Arial", 11), width=20).pack(anchor="w", pady=(4, 8))

    settings_frame._wa_account_id = tk.StringVar(value=wa_cfg.get("account_id", ""))
    settings_frame._wa_sender_id = tk.StringVar(value=wa_cfg.get("sender_id", ""))
    settings_frame._wa_api_key = tk.StringVar(value=load_whatsapp_provider_secret(settings_frame._wa_provider.get()))
    settings_frame._row_entry(wa_sec, "Account ID / App ID:", settings_frame._wa_account_id)
    settings_frame._row_entry(wa_sec, "Sender / Phone ID:", settings_frame._wa_sender_id)
    settings_frame._row_entry(wa_sec, "API Secret / Token:", settings_frame._wa_api_key, show="*", help_text="Stored securely when supported by the current Windows environment.")
    btn_row = tk.Frame(wa_sec, bg=C["card"])
    btn_row.pack(fill=tk.X, pady=(6, 0))
    ModernButton(btn_row, text="Validate Provider", command=settings_frame._validate_whatsapp_provider, color=C["blue"], hover_color="#154360", width=140, height=30, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
    ModernButton(btn_row, text="Test Message", command=settings_frame._test_whatsapp_provider, color=C["green"], hover_color="#1e8449", width=120, height=30, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=8)

    mb_cfg = cfg.get("multibranch_config", {})
    mb_sec = settings_frame._sec(body, "Multi-Branch Sync", C["orange"])
    tk.Label(mb_sec, text="Optional paid foundation for customer-owned VPS, NAS, office server, or LAN sync server.", bg=C["card"], fg=C["muted"], justify="left", font=("Arial", 10)).pack(anchor="w", pady=(0, 8))
    settings_frame._mb_enabled = tk.BooleanVar(value=mb_cfg.get("enabled", False))
    settings_frame._mb_auto_sync = tk.BooleanVar(value=mb_cfg.get("auto_sync", False))
    settings_frame._chk(mb_sec, "Enable Multi-Branch mode", settings_frame._mb_enabled)
    settings_frame._chk(mb_sec, "Enable automatic sync", settings_frame._mb_auto_sync)
    settings_frame._mb_server_url = tk.StringVar(value=mb_cfg.get("server_url", ""))
    settings_frame._mb_shop_id = tk.StringVar(value=mb_cfg.get("shop_id", ""))
    settings_frame._mb_api_key = tk.StringVar(value=load_multibranch_api_key())
    settings_frame._mb_interval = tk.StringVar(value=str(mb_cfg.get("sync_interval_minutes", 15)))
    settings_frame._row_entry(mb_sec, "Server URL:", settings_frame._mb_server_url, help_text="Example: https://sync.example.com or http://office-server:8000")
    settings_frame._row_entry(mb_sec, "Shop ID:", settings_frame._mb_shop_id, help_text="Example: branch-kochi or main-store")
    settings_frame._row_entry(mb_sec, "API Key:", settings_frame._mb_api_key, show="*", help_text="Paste the branch sync key issued for this shop.")
    settings_frame._row_entry(mb_sec, "Sync Interval (min):", settings_frame._mb_interval)
    btn_row2 = tk.Frame(mb_sec, bg=C["card"])
    btn_row2.pack(fill=tk.X, pady=(6, 0))
    ModernButton(btn_row2, text="Test Connection", command=settings_frame._test_multibranch_connection, color=C["blue"], hover_color="#154360", width=140, height=30, radius=8, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
    settings_frame._mb_status_lbl = tk.Label(mb_sec, text=f"Status: {mb_cfg.get('sync_status', 'Not Connected')}", bg=C["card"], fg=C["muted"], font=("Arial", 10, "bold"))
    settings_frame._mb_status_lbl.pack(anchor="w", pady=(10, 0))

    ops_sec = settings_frame._sec(body, "Developer Tools", C["blue"])
    tk.Label(ops_sec, text="These controls stay out of the main sidebar. Enable them only for customers who need advanced setup support.", bg=C["card"], fg=C["muted"], justify="left", font=("Arial", 10)).pack(anchor="w")

    exp_sec = settings_frame._sec(body, "Experimental Features", C["orange"])
    tk.Label(exp_sec, text="Mobile Viewer, WhatsApp API providers, and Multi-Branch sync are optional. Save settings, then reopen the related module to refresh its advanced UI.", bg=C["card"], fg=C["muted"], justify="left", font=("Arial", 10)).pack(anchor="w")

    settings_frame._savebtn(body, "Save Advanced Features", settings_frame._save_advanced)

