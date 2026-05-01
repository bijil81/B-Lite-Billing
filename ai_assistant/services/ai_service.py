"""
ai_service.py — AI Service Layer (Claude + OpenAI support)
============================================================
Supports both:
  - Anthropic Claude API
  - OpenAI GPT API (free tier: gpt-3.5-turbo)

Provider auto-detected from API key:
  sk-ant-...  → Claude
  sk-...      → OpenAI
"""
import os, json
from typing import Callable
from secure_store import load_ai_api_key
from branding import get_company_name

# ── Try import both libraries ─────────────────────────────
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .ai_tools import TOOL_DEFINITIONS

# ── Config ────────────────────────────────────────────────
CLAUDE_MODEL  = "claude-sonnet-4-5"
OPENAI_MODEL  = "gpt-3.5-turbo"   # free tier compatible
MAX_TOKENS    = 1024

SYSTEM_PROMPT = f"""You are an intelligent business assistant for {get_company_name()}.
You help the shop owner and staff with:
- Sales analysis and revenue queries
- Customer information and loyalty points
- Inventory and stock management
- Staff attendance and commissions
- Appointment scheduling
- Business insights and suggestions
- Creating invoices and sending WhatsApp messages

Always respond in the same language the user writes in (Malayalam or English).
When you need data, use the available tools — never guess numbers.
For action tools (create_invoice, send_whatsapp), always confirm with the user first.
Keep responses concise and business-focused.
Format currency as ₹ with Indian numbering."""


def _detect_provider(api_key: str) -> str:
    """Detect API provider from key prefix."""
    if not api_key:
        return "none"
    if api_key.startswith("sk-ant-"):
        return "claude"
    if api_key.startswith("sk-"):
        return "openai"
    return "unknown"


# ── Convert Claude tool format → OpenAI tool format ───────
def _tools_to_openai() -> list:
    """Convert TOOL_DEFINITIONS (Anthropic format) to OpenAI format."""
    result = []
    for t in TOOL_DEFINITIONS:
        result.append({
            "type": "function",
            "function": {
                "name":        t["name"],
                "description": t["description"],
                "parameters":  t["input_schema"],
            }
        })
    return result


# ── Convert message history for OpenAI ────────────────────
def _messages_to_openai(messages: list) -> list:
    """Convert Anthropic message format to OpenAI format."""
    out = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        role    = m.get("role", "user")
        content = m.get("content", "")

        if isinstance(content, str):
            out.append({"role": role, "content": content})

        elif isinstance(content, list):
            # Tool results from user turn
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        out.append({
                            "role":         "tool",
                            "tool_call_id": block.get("tool_use_id", ""),
                            "content":      block.get("content", ""),
                        })
                    elif block.get("type") == "tool_use":
                        # assistant tool_use block
                        out.append({
                            "role":    "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id":   block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name":      block.get("name", ""),
                                    "arguments": json.dumps(
                                        block.get("input", {}))
                                }
                            }]
                        })
    return out


class AIService:
    """
    Unified AI service — auto-detects Claude or OpenAI from API key.
    Same interface regardless of provider.
    """

    def __init__(self, api_key: str = ""):
        self.api_key  = api_key or load_ai_api_key() or os.environ.get("ANTHROPIC_API_KEY", "")
        self.provider = _detect_provider(self.api_key)
        self.model    = CLAUDE_MODEL
        self._claude  = None
        self._openai  = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            return
        self.provider = _detect_provider(self.api_key)

        if self.provider == "claude" and ANTHROPIC_AVAILABLE:
            try:
                self._claude = anthropic.Anthropic(api_key=self.api_key)
                self.model   = CLAUDE_MODEL
            except Exception as e:
                from utils import app_log
                app_log(f"[AIService] Claude init error: {e}")

        elif self.provider == "openai" and OPENAI_AVAILABLE:
            try:
                self._openai = openai.OpenAI(api_key=self.api_key)
                self.model   = OPENAI_MODEL
            except Exception as e:
                from utils import app_log
                app_log(f"[AIService] OpenAI init error: {e}")

        elif self.provider == "openai" and not OPENAI_AVAILABLE:
            from utils import app_log
            app_log("[AIService] openai package not installed. Run: pip install openai")

    def set_api_key(self, key: str):
        self.api_key = key
        self._claude = None
        self._openai = None
        self._init_client()

    def set_model(self, model: str):
        self.model = model

    def is_ready(self) -> bool:
        if self.provider == "claude":
            return self._claude is not None
        elif self.provider == "openai":
            return self._openai is not None
        return False

    def get_provider_name(self) -> str:
        return {"claude": "Claude (Anthropic)",
                "openai": "ChatGPT (OpenAI)",
                "none":   "Not configured",
                "unknown": "Unknown"}.get(self.provider, "Unknown")

    def send(self, messages: list,
             use_tools: bool = True,
             on_stream: Callable = None) -> dict:
        """Send messages — routes to correct provider."""
        if not self.is_ready():
            provider_hint = ""
            if self.provider == "openai" and not OPENAI_AVAILABLE:
                provider_hint = "\nRun: pip install openai"
            return {
                "type":    "error",
                "content": f"AI not configured. Add API key in Settings.{provider_hint}",
                "tool_calls": []
            }

        try:
            if self.provider == "claude":
                return self._send_claude(messages, use_tools)
            elif self.provider == "openai":
                return self._send_openai(messages, use_tools)
        except Exception as e:
            return {"type": "error",
                    "content": self._friendly_error(str(e)),
                    "tool_calls": []}

        return {"type": "error", "content": "Unknown provider.", "tool_calls": []}

    # ── Claude ───────────────────────────────────────────
    def _send_claude(self, messages: list, use_tools: bool) -> dict:
        kwargs = {
            "model":      self.model,
            "max_tokens": MAX_TOKENS,
            "system":     SYSTEM_PROMPT,
            "messages":   messages,
        }
        if use_tools:
            kwargs["tools"] = TOOL_DEFINITIONS

        response    = self._claude.messages.create(**kwargs)
        tool_calls  = []
        text_parts  = []
        stop_reason = getattr(response, "stop_reason", "end_turn")

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id":    block.id,
                    "name":  block.name,
                    "input": block.input,
                })

        if tool_calls:
            return {
                "type":        "tool_use",
                "content":     response.content,
                "tool_calls":  tool_calls,
                "stop_reason": stop_reason,
            }
        return {
            "type":        "text",
            "content":     "\n".join(text_parts),
            "tool_calls":  [],
            "stop_reason": stop_reason,
        }

    # ── OpenAI ───────────────────────────────────────────
    def _send_openai(self, messages: list, use_tools: bool) -> dict:
        oai_messages = _messages_to_openai(messages)

        kwargs = {
            "model":       self.model,
            "messages":    oai_messages,
            "max_tokens":  MAX_TOKENS,
        }
        if use_tools:
            kwargs["tools"]       = _tools_to_openai()
            kwargs["tool_choice"] = "auto"

        response = self._openai.chat.completions.create(**kwargs)
        choice   = response.choices[0]
        msg      = choice.message

        # Tool calls
        if msg.tool_calls:
            tool_calls = []
            # Build Anthropic-compatible content for history
            content_blocks = []
            for tc in msg.tool_calls:
                try:
                    inp = json.loads(tc.function.arguments)
                except Exception:
                    inp = {}
                tool_calls.append({
                    "id":    tc.id,
                    "name":  tc.function.name,
                    "input": inp,
                })
                content_blocks.append({
                    "type":  "tool_use",
                    "id":    tc.id,
                    "name":  tc.function.name,
                    "input": inp,
                })
            return {
                "type":        "tool_use",
                "content":     content_blocks,
                "tool_calls":  tool_calls,
                "stop_reason": "tool_use",
            }

        # Text response
        text = msg.content or ""
        return {
            "type":        "text",
            "content":     text,
            "tool_calls":  [],
            "stop_reason": "end_turn",
        }

    def _friendly_error(self, err: str) -> str:
        err_l = err.lower()
        if "credit" in err_l or "billing" in err_l or "balance" in err_l:
            if self.provider == "claude":
                return ("❌ Claude API credits finished.\n"
                        "Add credits: console.anthropic.com/settings/billing\n"
                        "Or use OpenAI key in Settings → AI Assistant.")
            return "❌ API credits finished. Please top up your account."
        if "authentication" in err_l or "api_key" in err_l or "invalid" in err_l:
            return "❌ Invalid API key. Check Settings → AI Assistant."
        if "rate_limit" in err_l:
            return "⚠️ Rate limit reached. Please wait a moment."
        if "model" in err_l:
            return f"❌ Model error: {err}"
        return f"AI error: {err}"
