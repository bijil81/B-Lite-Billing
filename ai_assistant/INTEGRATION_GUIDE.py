"""
HOW TO INTEGRATE AI ASSISTANT INTO main.py
============================================
Copy this patch into your existing main.py

STEP 1: Add import at top of main.py
STEP 2: Add AI tab to notebook  
STEP 3: Init controller in SalonApp.__init__
STEP 4: Add floating button after _build()
STEP 5: Add AI settings to salon_settings.py
"""

# ════════════════════════════════════════════════════════
# STEP 1 — Add these imports at top of main.py
# ════════════════════════════════════════════════════════
"""
# At top of main.py, after existing imports:
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from ai_assistant.controllers.ai_controller import AIController
from ai_assistant.ui.ai_chat_window import AIChatWindow, AIChatFrame
"""


# ════════════════════════════════════════════════════════
# STEP 2 — Add AI tab to the NAV list in SalonApp
# ════════════════════════════════════════════════════════
"""
# In SalonApp, find self.NAV = [...] and add:
("🤖", "AI Assistant", "ai_assistant", False),

# In _init_modules(), add:
"ai_assistant": AIChatFrame,
"""


# ════════════════════════════════════════════════════════
# STEP 3 — Init controller in SalonApp.__init__
# ════════════════════════════════════════════════════════
"""
# In SalonApp.__init__, after self._build():

# Load API key from settings
from salon_settings import get_settings
ai_cfg = get_settings().get("ai_config", {})
api_key = ai_cfg.get("api_key", "")

# Create controller (shared by floating + tab)
self.ai_ctrl = AIController(app_ref=self, api_key=api_key)

# Create floating chat button
self.ai_chat = AIChatWindow(self.root, self.ai_ctrl, app_ref=self)
"""


# ════════════════════════════════════════════════════════
# STEP 4 — Pass controller to AI tab frame
# ════════════════════════════════════════════════════════
"""
# In _init_modules(), when building ai_assistant frame:

def _build_ai_frame(parent):
    return AIChatFrame(parent, self.ai_ctrl)

# Or if you use the standard frame pattern:
self.frames["ai_assistant"] = AIChatFrame(
    self.content, self.ai_ctrl)
self.frames["ai_assistant"].pack(fill=tk.BOTH, expand=True)
self.frames["ai_assistant"].pack_forget()
"""


# ════════════════════════════════════════════════════════
# STEP 5 — Add AI settings to salon_settings.py
# ════════════════════════════════════════════════════════
"""
# In salon_settings.py _build() method, add a new settings section:

ai_section = self._sec(parent, "🤖  AI Assistant", C["accent"])

tk.Label(ai_section, text="Anthropic API Key:",
         bg=C["card"], fg=C["muted"],
         font=("Arial", 11)).pack(anchor="w")

self._ai_key_var = tk.StringVar(
    value=cfg.get("ai_config", {}).get("api_key", ""))
tk.Entry(ai_section, textvariable=self._ai_key_var,
         show="*", font=("Arial", 11),
         bg=C["input"], fg=C["text"], bd=0).pack(
             fill=tk.X, ipady=6, pady=(4,8))

self._ai_enabled = tk.BooleanVar(
    value=cfg.get("ai_config", {}).get("enabled", True))
tk.Checkbutton(ai_section, text="Enable AI Assistant",
               variable=self._ai_enabled,
               bg=C["card"], fg=C["text"],
               selectcolor=C["input"],
               font=("Arial", 11)).pack(anchor="w")

tk.Label(ai_section,
         text="Get your free API key at: console.anthropic.com",
         bg=C["card"], fg=C["muted"],
         font=("Arial", 10)).pack(anchor="w", pady=(4,0))

# In _save_settings():
cfg["ai_config"] = {
    "api_key": self._ai_key_var.get().strip(),
    "enabled": self._ai_enabled.get(),
}
"""


# ════════════════════════════════════════════════════════
# COMPLETE main.py PATCH (minimal, clean)
# ════════════════════════════════════════════════════════

MAIN_PY_PATCH = '''
# ── 1. Add at top of main.py ──────────────────────────────────────────────
from ai_assistant.controllers.ai_controller import AIController
from ai_assistant.ui.ai_chat_window import AIChatWindow, AIChatFrame

# ── 2. In NAV list, add ───────────────────────────────────────────────────
("🤖", "AI Assistant", "ai_assistant", False),

# ── 3. In _init_modules, add to modules dict ──────────────────────────────
"ai_assistant": lambda p: AIChatFrame(p, self.ai_ctrl),

# ── 4. In SalonApp.__init__, after self._build() ──────────────────────────
from salon_settings import get_settings
_ai_cfg = get_settings().get("ai_config", {})
self.ai_ctrl = AIController(
    app_ref = self,
    api_key = _ai_cfg.get("api_key", "")
)
if _ai_cfg.get("enabled", True):
    self.ai_chat = AIChatWindow(self.root, self.ai_ctrl, self)
'''


# ════════════════════════════════════════════════════════
# REQUIREMENTS
# ════════════════════════════════════════════════════════
REQUIREMENTS = """
# Install required packages:
pip install anthropic

# Optional (for WhatsApp):
pip install pywhatkit

# Your existing packages (already installed):
# tkinter, json, csv, os, threading — standard library
"""


if __name__ == "__main__":
    print("AI Assistant Integration Guide")
    print("=" * 50)
    print(MAIN_PY_PATCH)
    print("\nREQUIREMENTS:")
    print(REQUIREMENTS)
