import tkinter as tk


def render_theme_tab(settings_frame):
    from salon_settings import C, DEFAULTS, THEMES, ModernButton, get_action_icon, get_settings

    cfg = get_settings()
    body = settings_frame._scroll("theme")
    curr = cfg.get("theme", DEFAULTS["theme"])

    tk.Label(body, text="Theme Studio", bg=C["bg"], fg=C["accent"], font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 4))
    tk.Label(
        body,
        text="Use a cleaner palette system inspired by the upgraded V6 color family.",
        bg=C["bg"],
        fg=C["muted"],
        font=("Arial", 10),
    ).pack(anchor="w", pady=(0, 12))

    settings_frame._theme_var = tk.StringVar(value=curr)
    settings_frame._theme_note = tk.Label(
        body,
        text=f"Current theme: {THEMES.get(curr, THEMES[DEFAULTS['theme']])['name']}",
        bg=C["bg"],
        fg=C["lime"],
        font=("Arial", 10, "bold"),
    )
    settings_frame._theme_note.pack(anchor="w", pady=(0, 8))

    cards = tk.Frame(body, bg=C["bg"])
    cards.pack(fill=tk.X, pady=(0, 14))
    for col in range(3):
        cards.grid_columnconfigure(col, weight=1)

    theme_cards = []

    def _refresh_theme_cards():
        selected_key = settings_frame._theme_var.get()
        for entry in theme_cards:
            is_selected = entry["key"] == selected_key
            card_bg = C["card"]
            border = entry["theme"]["blue"] if is_selected else C["input"]
            entry["card"].configure(
                bg=card_bg,
                highlightbackground=border,
                highlightcolor=border,
                highlightthickness=2 if is_selected else 1,
                bd=0,
            )
            entry["top"].configure(bg=card_bg)
            entry["name_label"].configure(bg=card_bg, fg=entry["theme"]["blue"] if is_selected else C["text"])
            entry["active_badge"].configure(
                text="Selected" if is_selected else "",
                bg=card_bg,
                fg=entry["theme"]["accent"] if is_selected else card_bg,
            )
            entry["radio"].configure(
                bg=card_bg,
                fg=entry["theme"]["blue"] if is_selected else C["text"],
                activebackground=card_bg,
                activeforeground=entry["theme"]["blue"] if is_selected else C["text"],
                selectcolor=C["input"],
            )
            entry["info_label"].configure(bg=card_bg, fg=C["muted"])
            entry["swatches"].configure(bg=card_bg)

    def _select_theme(selected_key: str):
        settings_frame._theme_var.set(selected_key)
        settings_frame._theme_note.config(text=f"Selected theme: {THEMES[selected_key]['name']}")
        _refresh_theme_cards()

    for idx, (key, theme) in enumerate(THEMES.items()):
        card = tk.Frame(cards, bg=C["card"], padx=12, pady=12, highlightthickness=1, highlightbackground=theme["blue"] if key == curr else C["input"])
        row, col = divmod(idx, 3)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

        top = tk.Frame(card, bg=C["card"])
        top.pack(fill=tk.X)
        name_label = tk.Label(top, text=theme["name"], bg=C["card"], fg=C["text"], font=("Arial", 11, "bold"))
        name_label.pack(side=tk.LEFT)
        active_badge = tk.Label(
            top,
            text="Selected" if key == curr else "",
            bg=C["card"],
            fg=theme["accent"] if key == curr else C["card"],
            font=("Arial", 9, "bold"),
        )
        active_badge.pack(side=tk.RIGHT)

        swatches = tk.Frame(card, bg=C["card"], pady=8)
        swatches.pack(fill=tk.X)
        for color_key in ("sidebar", "card", "blue", "accent"):
            tk.Frame(swatches, bg=theme[color_key], width=36, height=18).pack(side=tk.LEFT, padx=(0, 6))

        info_label = tk.Label(card, text=f"BG {theme['bg']}  |  Card {theme['card']}", bg=C["card"], fg=C["muted"], font=("Arial", 9))
        info_label.pack(anchor="w", pady=(0, 8))
        radio = tk.Radiobutton(
            card,
            text="Use This Theme",
            variable=settings_frame._theme_var,
            value=key,
            bg=C["card"],
            fg=C["text"],
            selectcolor=C["input"],
            activebackground=C["card"],
            activeforeground=C["text"],
            command=lambda sk=key: _select_theme(sk),
            font=("Arial", 10, "bold"),
            cursor="hand2",
        )
        radio.pack(anchor="w")

        theme_cards.append(
            {
                "key": key,
                "theme": theme,
                "card": card,
                "top": top,
                "name_label": name_label,
                "active_badge": active_badge,
                "swatches": swatches,
                "info_label": info_label,
                "radio": radio,
            }
        )
        for widget in (card, top, swatches, name_label, active_badge, info_label):
            widget.bind("<Button-1>", lambda e, sk=key: _select_theme(sk))

    _refresh_theme_cards()

    scale_sec = settings_frame._sec(body, "\U0001f4cf  UI Scale")
    settings_frame._scale_var = tk.DoubleVar(value=cfg.get("ui_scale", 1.0))
    scale_row = tk.Frame(scale_sec, bg=C["bg"])
    scale_row.pack(fill=tk.X)
    for idx, (val, lbl) in enumerate([(0.7, "70%"), (0.8, "80%"), (0.9, "90%"), (1.0, "100%"), (1.1, "110%"), (1.2, "120%"), (1.5, "150%")]):
        tk.Radiobutton(
            scale_row,
            text=lbl,
            variable=settings_frame._scale_var,
            value=val,
            bg=C["bg"],
            fg=C["text"],
            selectcolor=C["input"],
            font=("Arial", 10),
            cursor="hand2",
        ).grid(row=idx // 4, column=idx % 4, padx=8, pady=4, sticky="w")

    logo_sec = settings_frame._sec(body, "\U0001f5bc\ufe0f  Logo")
    logo_row = tk.Frame(logo_sec, bg=C["bg"])
    logo_row.pack(fill=tk.X)
    settings_frame._logo_var = tk.StringVar(value=cfg.get("logo_path", ""))
    tk.Label(
        logo_row,
        textvariable=settings_frame._logo_var,
        bg=C["input"],
        fg=C["lime"],
        font=("Arial", 10),
        anchor="w",
        padx=6,
        pady=5,
    ).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ModernButton(
        logo_row,
        text="Browse",
        image=get_action_icon("browse"),
        compound="left",
        command=settings_frame._browse_logo,
        color=C["blue"],
        hover_color="#154360",
        width=90,
        height=32,
        radius=8,
        font=("Arial", 10, "bold"),
    ).pack(side=tk.LEFT, padx=(6, 0))

    ModernButton(
        body,
        text="Apply Theme & Save",
        image=get_action_icon("save"),
        compound="left",
        command=settings_frame._apply_theme,
        color=C["accent"],
        hover_color=C["purple"],
        width=240,
        height=40,
        radius=8,
        font=("Arial", 11, "bold"),
    ).pack(pady=(16, 6), anchor="w")
    tk.Label(body, text="* Full effect on next restart", bg=C["bg"], fg=C["muted"], font=("Arial", 9)).pack(anchor="w")

