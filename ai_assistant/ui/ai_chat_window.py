"""
ai_chat_window.py Ã¢â‚¬â€ AI Assistant Chat UI (Tkinter)
====================================================
Features:
- Floating popup button (bottom-right corner)
- Dedicated sidebar/panel chat window
- Chat bubbles (user=right, AI=left)
- Typing animation
- Tool activity indicator
- Action confirmation dialog
- AI on/off toggle
- Quick action buttons
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from branding import get_app_name
from src.blite_v6.app.window_lifecycle import hide_while_building, reveal_when_ready

try:
    from utils import C
except ImportError:
    C = {
        "bg": "#0f172a", "card": "#1e293b", "sidebar": "#162032",
        "text": "#e2e8f0", "muted": "#64748b", "input": "#1e293b",
        "teal": "#0ea5e9", "accent": "#8b5cf6", "green": "#22c55e",
        "red": "#ef4444", "orange": "#f97316", "blue": "#3b82f6",
        "lime": "#a3e635", "gold": "#f59e0b",
    }


# Ã¢â€â‚¬Ã¢â€â‚¬ Colors specific to chat UI Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
USER_BUBBLE_BG   = "#0ea5e9"   # teal Ã¢â‚¬â€ user messages
USER_BUBBLE_FG   = "white"
AI_BUBBLE_BG     = "#1e293b"   # card Ã¢â‚¬â€ AI messages
AI_BUBBLE_FG     = "#e2e8f0"
TOOL_BG          = "#162032"   # sidebar Ã¢â‚¬â€ tool activity
TOOL_FG          = "#64748b"
ACTION_BG        = "#f97316"   # orange Ã¢â‚¬â€ pending actions
ACTION_FG        = "white"
WINDOW_W         = 360
WINDOW_H         = 560
FLOAT_BTN_SIZE   = 48
FLOAT_BTN_MARGIN = 16
FLOAT_BTN_TOP_Y  = 84


class AIChatWindow:
    """
    Floating chat window + toggle button.
    Integrates with AIController.
    """

    def __init__(self, parent, controller, app_ref=None):
        self.parent     = parent
        self.ctrl       = controller
        self.app_ref    = app_ref
        self._visible   = False
        self._win       = None
        self._typing    = False
        self._dot_count = 0
        self._stream_buffer = []
        self._current_ai_bubble = None

        # Wire controller callbacks
        self.ctrl.on_response      = self._on_response
        self.ctrl.on_tool_activity = self._on_tool_activity
        self.ctrl.on_error         = self._on_error
        self.ctrl.on_action_needed = self._on_action_needed
        self.ctrl.on_typing_start  = self._on_typing_start
        self.ctrl.on_typing_stop   = self._on_typing_stop
        self.ctrl.on_stream_token  = self._on_stream_token

        # Create floating toggle button
        self._build_float_btn()

    # Ã¢â€â‚¬Ã¢â€â‚¬ Floating button Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build_float_btn(self):
        """Top-right floating AI button kept clear of page action bars."""
        self._float_btn = tk.Button(
            self.parent,
            text="AI",
            command=self.toggle,
            bg=C["accent"],
            fg="white",
            font=("Arial", 16, "bold"),
            bd=0,
            cursor="hand2",
            relief="flat",
            width=3,
            height=1,
        )
        # Place at top-right so it does not overlap billing action buttons.
        self.parent.update_idletasks()
        self._position_float_btn()
        self.parent.bind("<Configure>", lambda e: self._position_float_btn())

        # Pulse effect when AI is thinking
        self._float_pulsing = False

    def _position_float_btn(self):
        try:
            notif_btn = getattr(self.app_ref, "btn_notifications", None)
            top_bar = getattr(self.app_ref, "top_bar", None)
            if notif_btn and top_bar and notif_btn.winfo_exists() and top_bar.winfo_exists():
                self.parent.update_idletasks()
                x = notif_btn.winfo_x() - FLOAT_BTN_SIZE - 8
                y = top_bar.winfo_y() + max(6, (top_bar.winfo_height() - FLOAT_BTN_SIZE) // 2)
            else:
                w = self.parent.winfo_width()
                x = max(FLOAT_BTN_MARGIN, w - FLOAT_BTN_SIZE - FLOAT_BTN_MARGIN)
                y = FLOAT_BTN_TOP_Y
            self._float_btn.place(
                x=x,
                y=y,
                width=FLOAT_BTN_SIZE,
                height=FLOAT_BTN_SIZE,
            )
        except Exception:
            pass

    # Ã¢â€â‚¬Ã¢â€â‚¬ Toggle chat window Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self):
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._build_window()
        self._visible = True
        self._float_btn.configure(bg=C["teal"])

    def hide(self):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
        self._visible = False
        self._float_btn.configure(bg=C["accent"])

    # Ã¢â€â‚¬Ã¢â€â‚¬ Chat window Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _build_window(self):
        """Build the chat popup window."""
        self._win = tk.Toplevel(self.parent)
        hide_while_building(self._win)
        self._win.title(f"{get_app_name()} AI Assistant")
        self._win.configure(bg=C["bg"])
        self._win.resizable(True, True)
        self._win.protocol("WM_DELETE_WINDOW", self.hide)

        # Position top-right of parent
        try:
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = self.parent.winfo_width()
            self._win.geometry(
                f"{WINDOW_W}x{WINDOW_H}+"
                f"{px + pw - WINDOW_W - 10}+{py + 60}"
            )
        except Exception:
            self._win.geometry(f"{WINDOW_W}x{WINDOW_H}+100+100")

        self._win.attributes("-topmost", False)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Header Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        hdr = tk.Frame(self._win, bg=C["sidebar"], pady=8)
        hdr.pack(fill=tk.X)

        tk.Label(hdr, text="AI Assistant",
                 font=("Arial", 12, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(side=tk.LEFT, padx=12)

        # AI toggle
        self._ai_var = tk.BooleanVar(value=self.ctrl.enabled)
        tk.Checkbutton(hdr,
                       text="ON",
                       variable=self._ai_var,
                       command=self._toggle_ai,
                       bg=C["sidebar"], fg=C["teal"],
                       selectcolor=C["sidebar"],
                       font=("Arial", 10, "bold"),
                       cursor="hand2").pack(side=tk.RIGHT, padx=6)

        # Reset button
        tk.Button(hdr, text="Reset",
                  command=self._reset_chat,
                  bg=C["sidebar"], fg=C["muted"],
                  font=("Arial", 12), bd=0,
                  cursor="hand2").pack(side=tk.RIGHT)

        tk.Frame(self._win, bg=C["teal"], height=2).pack(fill=tk.X)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Chat area Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        chat_frame = tk.Frame(self._win, bg=C["bg"])
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(chat_frame, bg=C["bg"],
                                  highlightthickness=0)
        vsb = ttk.Scrollbar(chat_frame, orient="vertical",
                             command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._chat_body = tk.Frame(self._canvas, bg=C["bg"])
        self._cwin = self._canvas.create_window(
            (0, 0), window=self._chat_body, anchor="nw")

        self._chat_body.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(
                self._cwin, width=e.width))

        # Mouse wheel scroll
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(
                -1 if e.delta > 0 else 1, "units"))

        # Typing indicator
        self._typing_lbl = tk.Label(self._chat_body, text="",
                                     bg=C["bg"], fg=C["muted"],
                                     font=("Arial", 10, "italic"))

        # Tool activity label
        self._tool_lbl = tk.Label(self._chat_body, text="",
                                   bg=C["bg"], fg=C["gold"],
                                   font=("Arial", 9))

        # Ã¢â€â‚¬Ã¢â€â‚¬ Quick actions Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        qa_frame = tk.Frame(self._win, bg=C["sidebar"], padx=8, pady=6)
        qa_frame.pack(fill=tk.X)
        tk.Label(qa_frame, text="Quick Tasks",
                 bg=C["sidebar"], fg=C["muted"],
                 font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(2, 8))

        quick = [
            ("Today Sales", "Today sales ethra?"),
            ("Low Stock",  "Low stock items?"),
            ("Appointments",  "Today appointments?"),
            ("Suggestions",   "Business suggestions please"),
        ]
        for label, prompt in quick:
            tk.Button(qa_frame, text=label,
                      command=lambda p=prompt: self._quick_send(p),
                      bg=C["card"], fg=C["text"],
                      font=("Arial", 9), bd=0,
                      padx=8, pady=4,
                      cursor="hand2").pack(side=tk.LEFT, padx=2)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Input area Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        inp_frame = tk.Frame(self._win, bg=C["card"], pady=8, padx=8)
        inp_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self._input_var = tk.StringVar()
        self._input_ent = tk.Entry(
            inp_frame,
            textvariable=self._input_var,
            font=("Arial", 11),
            bg=C["input"], fg=C["text"],
            bd=0, insertbackground=C["accent"],
        )
        self._input_ent.pack(side=tk.LEFT, fill=tk.X,
                              expand=True, ipady=8, padx=(0, 8))
        self._input_ent.bind("<Return>", lambda e: self._send())
        self._input_ent.focus_set()

        self._send_btn = tk.Button(
            inp_frame,
            text="Send",
            command=self._send,
            bg=C["accent"], fg="white",
            font=("Arial", 12, "bold"), bd=0,
            padx=12, pady=6,
            cursor="hand2",
        )
        self._send_btn.pack(side=tk.RIGHT)

        # Welcome message
        self._add_bubble(
"Hello! I'm your AI shop assistant.\n"
            "Ask me about sales, customers, stock, or say\n"
            "'Create bill: Haircut 200' to start billing!",
            role="assistant"
        )
        reveal_when_ready(self._win)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Chat bubbles Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _add_bubble(self, text: str, role: str = "assistant") -> tk.Label:
        """Add a chat bubble to the chat body."""
        is_user = role == "user"
        outer   = tk.Frame(self._chat_body, bg=C["bg"])
        outer.pack(fill=tk.X, pady=(4, 0),
                   padx=(60 if is_user else 8, 8 if is_user else 60))

        bubble = tk.Label(
            outer,
            text=text,
            font=("Arial", 10),
            bg=USER_BUBBLE_BG if is_user else AI_BUBBLE_BG,
            fg=USER_BUBBLE_FG if is_user else AI_BUBBLE_FG,
            wraplength=WINDOW_W - 90,
            justify="left",
            padx=12, pady=8,
            relief="flat",
            anchor="w",
        )
        bubble.pack(side=tk.RIGHT if is_user else tk.LEFT)

        # Role label
        role_lbl = tk.Label(outer,
                             text="You" if is_user else "AI",
                             bg=C["bg"], fg=C["muted"],
                             font=("Arial", 8))
        role_lbl.pack(side=tk.RIGHT if is_user else tk.LEFT,
                      anchor="s", padx=4)

        self._scroll_bottom()
        return bubble

    def _add_tool_card(self, text: str):
        """Small tool-activity indicator."""
        f = tk.Frame(self._chat_body, bg=TOOL_BG,
                     padx=8, pady=4)
        f.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(f, text=f"Tool: {text}",
                 bg=TOOL_BG, fg=TOOL_FG,
                 font=("Arial", 9, "italic")).pack(anchor="w")
        self._scroll_bottom()

    def _add_action_card(self, action: dict):
        """Confirmation card for pending actions."""
        f = tk.Frame(self._chat_body, bg=ACTION_BG,
                     padx=10, pady=8)
        f.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(f, text="Action Required",
                 bg=ACTION_BG, fg="white",
                 font=("Arial", 10, "bold")).pack(anchor="w")

        tk.Label(f, text=action.get("summary", ""),
                 bg=ACTION_BG, fg="white",
                 font=("Arial", 10),
                 wraplength=WINDOW_W - 40,
                 justify="left").pack(anchor="w", pady=(4, 8))

        btn_row = tk.Frame(f, bg=ACTION_BG)
        btn_row.pack(fill=tk.X)

        tk.Button(btn_row, text="Confirm",
                  command=lambda: self._do_confirm(True, f),
                  bg="#22c55e", fg="white",
                  font=("Arial", 10, "bold"), bd=0,
                  padx=12, pady=4,
                  cursor="hand2").pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(btn_row, text="Cancel",
                  command=lambda: self._do_confirm(False, f),
                  bg=C["card"], fg=C["text"],
                  font=("Arial", 10), bd=0,
                  padx=12, pady=4,
                  cursor="hand2").pack(side=tk.LEFT)

        self._scroll_bottom()

    # Ã¢â€â‚¬Ã¢â€â‚¬ Interaction Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _send(self):
        msg = self._input_var.get().strip()
        if not msg:
            return
        self._input_var.set("")
        self._add_bubble(msg, role="user")
        self._send_btn.configure(state="disabled")
        self.ctrl.send_message(msg)

    def _quick_send(self, prompt: str):
        if not self._win or not self._win.winfo_exists():
            self.show()
        self._input_var.set(prompt)
        self._send()

    def _do_confirm(self, confirmed: bool, card_frame: tk.Frame):
        """Handle action confirm/cancel."""
        try:
            card_frame.destroy()
        except Exception:
            pass
        status = "confirmed" if confirmed else "cancelled"
        self._add_bubble(f"Action {status}.", role="user")
        self.ctrl.confirm_action(confirmed)

    def _toggle_ai(self):
        enabled = self._ai_var.get()
        self.ctrl.toggle_ai(enabled)
        status = "enabled" if enabled else "disabled"
        self._add_tool_card(f"AI assistant {status}")

    def _reset_chat(self):
        if messagebox.askyesno("Reset", "Clear chat history?",
                                parent=self._win):
            self.ctrl.reset_conversation()
            for w in self._chat_body.winfo_children():
                w.destroy()
            self._add_bubble(
                "Chat cleared. How can I help you?",
                role="assistant")

    # Ã¢â€â‚¬Ã¢â€â‚¬ Controller callbacks (called from thread) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _on_response(self, text: str, role: str = "assistant"):
        self._safe_call(lambda: self._add_bubble(text, role))

    def _on_tool_activity(self, msg: str):
        self._safe_call(lambda: self._add_tool_card(msg))

    def _on_error(self, msg: str):
        def _show_error_message():
            self._add_bubble(f"Error: {msg}", role="assistant")
            try:
                self._send_btn.configure(state="normal")
            except Exception:
                pass
        self._safe_call(_show_error_message)

    def _on_action_needed(self, action: dict):
        def _show_action_card():
            self._add_action_card(action)
            self._send_btn.configure(state="normal")
        self._safe_call(_show_action_card)

    def _on_typing_start(self):
        def _show_typing_start():
            self._typing = True
            self._dot_count = 0
            self._animate_typing()
            self._send_btn.configure(state="disabled")
        self._safe_call(_show_typing_start)

    def _on_typing_stop(self):
        def _show_typing_stop():
            self._typing = False
            try:
                self._typing_lbl.configure(text="")
                self._tool_lbl.configure(text="")
                self._send_btn.configure(state="normal")
            except Exception:
                pass
        self._safe_call(_show_typing_stop)

    def _on_stream_token(self, token: str):
        """Handle streaming tokens Ã¢â‚¬â€ update last AI bubble."""
        self._stream_buffer.append(token)
        self._safe_call(self._flush_stream)

    def _flush_stream(self):
        if not self._stream_buffer:
            return
        chunk = "".join(self._stream_buffer)
        self._stream_buffer.clear()

        if self._current_ai_bubble is None:
            self._current_ai_bubble = self._add_bubble("", role="assistant")

        current_text = self._current_ai_bubble.cget("text")
        self._current_ai_bubble.configure(text=current_text + chunk)
        self._scroll_bottom()

    # Ã¢â€â‚¬Ã¢â€â‚¬ Helpers Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    def _animate_typing(self):
        if not self._typing:
            return
        dots = "." * ((self._dot_count % 3) + 1)
        try:
            self._typing_lbl.configure(text=f"  AI is thinking {dots}")
            self._typing_lbl.pack(anchor="w", padx=12)
        except Exception:
            return
        self._dot_count += 1
        try:
            self._win.after(400, self._animate_typing)
        except Exception:
            pass

    def _scroll_bottom(self):
        try:
            self._canvas.update_idletasks()
            self._canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _safe_call(self, fn):
        """Schedule UI update on main thread Ã¢â‚¬â€ only if window is built."""
        try:
            # Only run if chat window is open and _chat_body exists
            if (self._win and self._win.winfo_exists()
                    and hasattr(self, "_chat_body")
                    and self._chat_body.winfo_exists()):
                self._win.after(0, fn)
            # else: window not open Ã¢â‚¬â€ silently drop (user will see on next open)
        except Exception:
            pass


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
# DEDICATED TAB VERSION (for main notebook)
# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
class AIChatFrame(tk.Frame):
    """
    Full-page AI chat tab.
    Drop into main notebook as a tab.
    Shares the same AIController as the floating window.
    """

    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self.ctrl = controller
        self._build()

        # Wire callbacks (shared with floating window)
        self.ctrl.on_response      = self._on_response
        self.ctrl.on_tool_activity = self._on_tool_activity
        self.ctrl.on_error         = self._on_error
        self.ctrl.on_action_needed = self._on_action_needed
        self.ctrl.on_typing_start  = self._on_typing_start
        self.ctrl.on_typing_stop   = self._on_typing_stop

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C["card"], pady=10)
        hdr.pack(fill=tk.X)
        lf = tk.Frame(hdr, bg=C["card"])
        lf.pack(side=tk.LEFT, padx=20)
        tk.Label(lf, text="AI Business Assistant",
                 font=("Arial", 15, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(lf, text="Ask about sales, customers, stock, appointments, or invoice actions",
                 font=("Arial", 10),
                 bg=C["card"], fg=C["muted"]).pack(anchor="w")

        self._ai_var = tk.BooleanVar(value=self.ctrl.enabled)
        tk.Checkbutton(hdr, text="AI ON",
                       variable=self._ai_var,
                       command=self._toggle_ai,
                       bg=C["card"], fg=C["teal"],
                       selectcolor=C["card"],
                       font=("Arial", 10, "bold"),
                       cursor="hand2").pack(side=tk.RIGHT, padx=15)
        tk.Frame(self, bg=C["teal"], height=2).pack(fill=tk.X)

        # Quick actions
        intro = tk.Frame(self, bg=C["card"], padx=16, pady=10)
        intro.pack(fill=tk.X, padx=15, pady=(10, 8))
        tk.Label(intro, text="AI Workspace",
                 bg=C["card"], fg=C["text"],
                 font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(intro,
                 text="Use quick prompts for common business questions, or ask in plain language for sales, stock, and customer insights.",
                 bg=C["card"], fg=C["muted"],
                 font=("Arial", 10), justify="left").pack(anchor="w", pady=(4, 0))

        qa = tk.Frame(self, bg=C["sidebar"], pady=6, padx=10)
        qa.pack(fill=tk.X)
        tk.Label(qa, text="Quick Tasks", bg=C["sidebar"],
                 fg=C["muted"], font=("Arial", 10)).pack(side=tk.LEFT)
        for label, prompt in [
            ("Today Sales",    "Today sales ethra?"),
            ("Low Stock",      "Low stock items list"),
            ("Top Customers",  "Top 5 customers this month"),
            ("Appointments",   "Today appointments"),
            ("Suggestions",    "Business improvement suggestions"),
        ]:
            tk.Button(qa, text=label,
                      command=lambda p=prompt: self._quick_send(p),
                      bg=C["card"], fg=C["text"],
                      font=("Arial", 9), bd=0, padx=8, pady=4,
                      cursor="hand2").pack(side=tk.LEFT, padx=4)

        # Split: chat | context
        split = tk.Frame(self, bg=C["bg"])
        split.pack(fill=tk.BOTH, expand=True)

        # Chat area (left)
        chat_f = tk.Frame(split, bg=C["bg"])
        chat_f.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(chat_f, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(chat_f, orient="vertical",
                             command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._body = tk.Frame(self._canvas, bg=C["bg"])
        self._cwin = self._canvas.create_window(
            (0,0), window=self._body, anchor="nw")
        self._body.bind("<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._cwin, width=e.width))

        # Tool label
        self._tool_lbl = tk.Label(self._body, text="",
                                   bg=C["bg"], fg=C["gold"],
                                   font=("Arial", 9, "italic"))

        # Input
        inp = tk.Frame(self, bg=C["card"], pady=10, padx=15)
        inp.pack(fill=tk.X, side=tk.BOTTOM)

        self._var = tk.StringVar()
        self._ent = tk.Entry(inp, textvariable=self._var,
                              font=("Arial", 12),
                              bg=C["input"], fg=C["text"],
                              bd=0, insertbackground=C["accent"])
        self._ent.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10)
        self._ent.bind("<Return>", lambda e: self._send())

        self._btn = tk.Button(inp, text="Send",
                               command=self._send,
                               bg=C["accent"], fg="white",
                               font=("Arial", 11, "bold"), bd=0,
                               padx=14, pady=8, cursor="hand2")
        self._btn.pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(inp, text="Clear",
                  command=self._reset,
                  bg=C["sidebar"], fg=C["muted"],
                  font=("Arial", 10), bd=0,
                  padx=8, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=4)

        # Welcome
        self._bubble("Hello! I'm your AI shop assistant.\n\n"
                     "I can answer questions about your business data\n"
                     "and perform actions like creating invoices.\n\n"
                     "Try asking: 'Today sales ethra?' or 'Low stock?'",
                     role="assistant")

    def _bubble(self, text, role="assistant"):
        is_user = role == "user"
        bg = USER_BUBBLE_BG if is_user else AI_BUBBLE_BG
        fg = USER_BUBBLE_FG if is_user else AI_BUBBLE_FG

        outer = tk.Frame(self._body, bg=C["bg"])
        outer.pack(fill=tk.X, padx=12, pady=(4,0))

        lbl = tk.Label(outer, text=text,
                        bg=bg, fg=fg,
                        font=("Arial", 10),
                        wraplength=520,
                        justify="left",
                        padx=14, pady=10, anchor="w")
        lbl.pack(side=tk.RIGHT if is_user else tk.LEFT)

        tk.Label(outer,
                 text="You" if is_user else "AI",
                 bg=C["bg"], fg=C["muted"],
                 font=("Arial", 8)).pack(
                     side=tk.RIGHT if is_user else tk.LEFT,
                     anchor="s", padx=4)
        self._scroll()
        return lbl

    def _send(self):
        msg = self._var.get().strip()
        if not msg: return
        self._var.set("")
        self._bubble(msg, role="user")
        self._btn.configure(state="disabled")
        self.ctrl.send_message(msg)

    def _quick_send(self, p):
        self._var.set(p)
        self._send()

    def _reset(self):
        self.ctrl.reset_conversation()
        for w in self._body.winfo_children():
            w.destroy()
        self._bubble("Chat cleared. How can I help?", role="assistant")

    def _toggle_ai(self):
        enabled = self._ai_var.get()
        self.ctrl.toggle_ai(enabled)

    def _on_response(self, text, role="assistant"):
        self.after(0, lambda: (self._bubble(text, role), self._btn.configure(state="normal")))

    def _on_tool_activity(self, msg):
        def _show_tool_activity():
            f = tk.Frame(self._body, bg=TOOL_BG, padx=8, pady=3)
            f.pack(fill=tk.X, padx=12, pady=2)
            tk.Label(f, text=f"Tool: {msg}", bg=TOOL_BG,
                     fg=TOOL_FG, font=("Arial",9,"italic")).pack(anchor="w")
            self._scroll()
        self.after(0, _show_tool_activity)

    def _on_error(self, msg):
        self.after(0, lambda: (
            self._bubble(f"Error: {msg}", role="assistant"),
            self._btn.configure(state="normal")
        ))

    def _on_action_needed(self, action):
        def _show_action_request():
            f = tk.Frame(self._body, bg=ACTION_BG, padx=12, pady=10)
            f.pack(fill=tk.X, padx=12, pady=6)
            tk.Label(f, text="Confirmation Required",
                     bg=ACTION_BG, fg="white",
                     font=("Arial",11,"bold")).pack(anchor="w")
            tk.Label(f, text=action.get("summary",""),
                     bg=ACTION_BG, fg="white",
                     font=("Arial",10),
                     wraplength=500, justify="left").pack(anchor="w", pady=(4,8))
            br = tk.Frame(f, bg=ACTION_BG)
            br.pack(fill=tk.X)
            tk.Button(br, text="Confirm",
                      command=lambda: (f.destroy(),
                                       self._bubble("Confirmed","user"),
                                       self.ctrl.confirm_action(True)),
                      bg="#22c55e", fg="white",
                      font=("Arial",10,"bold"), bd=0,
                      padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(0,8))
            tk.Button(br, text="Cancel",
                      command=lambda: (f.destroy(),
                                       self._bubble("Cancelled","user"),
                                       self.ctrl.confirm_action(False)),
                      bg=C["card"], fg=C["text"],
                      font=("Arial",10), bd=0,
                      padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT)
            self._scroll()
            self._btn.configure(state="normal")
        self.after(0, _show_action_request)

    def _on_typing_start(self):
        self.after(0, lambda: self._btn.configure(state="disabled"))

    def _on_typing_stop(self):
        self.after(0, lambda: self._btn.configure(state="normal"))

    def _scroll(self):
        try:
            self._canvas.update_idletasks()
            self._canvas.yview_moveto(1.0)
        except Exception:
            pass

    def refresh(self):
        pass
