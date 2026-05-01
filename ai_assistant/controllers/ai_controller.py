"""
ai_controller.py — Bridge between Chat UI and AI Agent
========================================================
Handles:
- Threading (non-blocking UI)
- Action confirmation popups
- AI enable/disable toggle
- Action logging
"""
import threading, json, os
from datetime import datetime
from typing import Callable
from branding import get_appdata_dir_name

from ai_assistant.services.ai_agent import AIAgent

try:
    from utils import DATA_DIR, app_log
except ImportError:
    DATA_DIR = os.path.join(os.environ.get("APPDATA",""), get_appdata_dir_name())
    def app_log(msg): print(msg)

AI_LOG_FILE = os.path.join(DATA_DIR, "ai_actions.log")


class AIController:
    """
    Central controller for AI assistant.
    UI calls: send_message(), confirm_action(), toggle_ai()
    Controller calls back: on_response(), on_tool_activity(), on_error()
    """

    def __init__(self, app_ref=None, api_key: str = ""):
        self.app_ref   = app_ref
        self.agent     = AIAgent(api_key)
        self.enabled   = True
        self._lock     = threading.Lock()
        self._busy     = False

        # Callbacks set by UI
        self.on_response:      Callable = None
        self.on_tool_activity: Callable = None
        self.on_error:         Callable = None
        self.on_action_needed: Callable = None
        self.on_typing_start:  Callable = None
        self.on_typing_stop:   Callable = None
        self.on_stream_token:  Callable = None

    # ── Config ──────────────────────────────────────────
    def set_api_key(self, key: str):
        self.agent.set_api_key(key)

    def toggle_ai(self, enable: bool = None):
        if enable is None:
            self.enabled = not self.enabled
        else:
            self.enabled = enable
        return self.enabled

    def is_ready(self) -> bool:
        return self.enabled and self.agent.is_ready()

    def is_busy(self) -> bool:
        return self._busy

    def reset_conversation(self):
        self.agent.reset()

    # ── Main entry point ─────────────────────────────────
    def send_message(self, user_message: str):
        """Called by UI when user sends a message. Non-blocking."""
        if not self.enabled:
            self._fire("on_error", "AI assistant is currently disabled. Enable it in Settings.")
            return

        if not self.agent.is_ready():
            self._fire("on_error",
                       "API key not configured.\n"
                       "Go to Settings → AI Assistant → Enter API key.")
            return

        if self._busy:
            self._fire("on_error", "Please wait for the current response.")
            return

        thread = threading.Thread(
            target=self._run_chat,
            args=(user_message,),
            daemon=True
        )
        thread.start()

    def _run_chat(self, user_message: str):
        with self._lock:
            self._busy = True

        try:
            self._fire("on_typing_start")

            result = self.agent.chat(
                user_message    = user_message,
                on_stream       = self._on_stream_token,
                on_tool_call    = self._on_tool_call,
            )

            self._fire("on_typing_stop")

            if result["type"] == "text":
                self._fire("on_response", result["content"], "assistant")

            elif result["type"] == "action_pending":
                # Need user confirmation
                self._fire("on_action_needed", result["action"])

            elif result["type"] == "error":
                self._fire("on_error", result["content"])

        except Exception as e:
            self._fire("on_typing_stop")
            self._fire("on_error", f"Unexpected error: {e}")
            app_log(f"[AIController._run_chat] {e}")
        finally:
            with self._lock:
                self._busy = False

    # ── Action confirmation ──────────────────────────────
    def confirm_action(self, confirmed: bool):
        """Called when user confirms or cancels a pending action."""
        thread = threading.Thread(
            target=self._run_confirm,
            args=(confirmed,),
            daemon=True
        )
        thread.start()

    def _run_confirm(self, confirmed: bool):
        with self._lock:
            self._busy = True
        try:
            self._fire("on_typing_start")
            result = self.agent.confirm_action(confirmed, self.app_ref)
            self._fire("on_typing_stop")

            action_word = "confirmed" if confirmed else "cancelled"
            self._log_action(action_word, result)

            if result["type"] == "text":
                self._fire("on_response", result["content"], "assistant")
            elif result["type"] == "error":
                self._fire("on_error", result["content"])
        except Exception as e:
            self._fire("on_typing_stop")
            app_log(f"[AIController._run_confirm] {e}")
        finally:
            with self._lock:
                self._busy = False

    # ── Callbacks ────────────────────────────────────────
    def _on_stream_token(self, token: str):
        self._fire("on_stream_token", token)

    def _on_tool_call(self, tool_name: str):
        labels = {
            "get_today_sales":        "Fetching today's sales...",
            "get_monthly_summary":    "Analyzing monthly data...",
            "get_top_services":       "Checking top services...",
            "get_customer_details":   "Looking up customer...",
            "check_low_stock":        "Checking inventory...",
            "get_appointments_today": "Loading appointments...",
            "get_staff_summary":      "Getting staff summary...",
            "get_birthday_customers": "Checking birthdays...",
            "get_expenses_summary":   "Analyzing expenses...",
            "suggest_offers":         "Generating suggestions...",
            "search_customers":       "Searching customers...",
            "create_invoice":         "Preparing invoice...",
            "send_whatsapp_message":  "Preparing message...",
        }
        msg = labels.get(tool_name, f"Running {tool_name}...")
        self._fire("on_tool_activity", msg)

    def _fire(self, event: str, *args):
        """Safely call a UI callback."""
        cb = getattr(self, event, None)
        if callable(cb):
            try:
                self._safe_ui(cb, *args)
            except Exception as e:
                app_log(f"[AIController._fire:{event}] {e}")

    def _safe_ui(self, fn: Callable, *args):
        root = getattr(self.app_ref, "root", None)
        if root is not None and hasattr(root, "after"):
            root.after(0, lambda: fn(*args))
        else:
            fn(*args)

    def _log_action(self, action_word: str, result: dict):
        """Log AI-triggered actions to file."""
        try:
            with open(AI_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                    f"[{action_word.upper()}] {json.dumps(result)}\n"
                )
        except Exception:
            pass
