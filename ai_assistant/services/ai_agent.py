"""
ai_agent.py — AI Agent with Tool-Calling Loop
===============================================
Manages conversation history.
Decides when to call tools vs respond directly.
Handles multi-step tool chains.
"""
import json
from typing import Callable

from .ai_service import AIService
from .ai_tools   import dispatch_tool, ACTION_TOOLS


class AIAgent:
    """
    Intelligent agent that:
    1. Sends user message to Claude
    2. If Claude wants a tool → calls it → sends result back
    3. Loops until final text response
    4. For action tools → returns pending action for confirmation
    """

    MAX_TOOL_LOOPS = 5   # prevent infinite loops

    def __init__(self, api_key: str = ""):
        self.service  = AIService(api_key)
        self.history  = []   # conversation history
        self._pending_action = None   # waiting for confirmation

    def set_api_key(self, key: str):
        self.service.set_api_key(key)

    def is_ready(self) -> bool:
        return self.service.is_ready()

    def reset(self):
        """Clear conversation history."""
        self.history = []
        self._pending_action = None

    def chat(self, user_message: str,
             on_stream: Callable = None,
             on_tool_call: Callable = None) -> dict:
        """
        Process a user message.

        Returns:
        {
            "type":    "text" | "action_pending" | "error",
            "content": str,
            "action":  dict | None   (if type == action_pending)
        }

        on_stream(text_chunk)  — called for each streaming token
        on_tool_call(name)     — called when a tool is being called
        """
        # Add user message to history
        self.history.append({
            "role":    "user",
            "content": user_message
        })

        loops = 0
        while loops < self.MAX_TOOL_LOOPS:
            loops += 1

            # Send to Claude
            result = self.service.send(
                messages  = self.history,
                use_tools = True,
                on_stream = on_stream if result_type_check(loops) else None
            )

            if result["type"] == "error":
                return {"type": "error", "content": result["content"]}

            if result["type"] == "text":
                # Final text response
                self.history.append({
                    "role":    "assistant",
                    "content": result["content"]
                })
                return {"type": "text", "content": result["content"]}

            if result["type"] == "tool_use":
                # Claude wants to call one or more tools
                tool_calls = result["tool_calls"]
                raw_content = result["content"]   # raw for history

                # Add assistant's tool_use block to history
                self.history.append({
                    "role":    "assistant",
                    "content": raw_content
                })

                # Process each tool call
                tool_results = []
                pending_action = None

                for tc in tool_calls:
                    tool_name  = tc["name"]
                    tool_input = tc["input"]
                    tool_id    = tc["id"]

                    if on_tool_call:
                        on_tool_call(tool_name)

                    # Execute tool
                    tool_result = dispatch_tool(tool_name, tool_input)

                    # Check if it's an action requiring confirmation
                    if (tool_name in ACTION_TOOLS and
                            tool_result.get("requires_confirmation")):
                        pending_action = {
                            "tool_id":   tool_id,
                            "tool_name": tool_name,
                            "data":      tool_result.get("data", {}),
                            "summary":   tool_result.get("summary", ""),
                        }
                        # Don't execute — return for confirmation
                        tool_result = {
                            "status":  "awaiting_confirmation",
                            "message": f"Action '{tool_name}' requires user confirmation."
                        }

                    tool_results.append({
                        "type":       "tool_result",
                        "tool_use_id": tool_id,
                        "content":    json.dumps(tool_result, ensure_ascii=False)
                    })

                # Add tool results to history
                self.history.append({
                    "role":    "user",
                    "content": tool_results
                })

                # If there's a pending action, pause loop and return
                if pending_action:
                    self._pending_action = pending_action
                    return {
                        "type":    "action_pending",
                        "content": pending_action["summary"],
                        "action":  pending_action
                    }
                # else loop back — Claude will see results and respond

        return {
            "type":    "error",
            "content": "Agent loop limit reached. Please try again."
        }

    def confirm_action(self, confirmed: bool, app_ref=None) -> dict:
        """
        Called after user confirms/cancels a pending action.
        If confirmed: execute the action via app_ref.
        Then continue the conversation loop.
        """
        if not self._pending_action:
            return {"type": "error", "content": "No pending action."}

        action = self._pending_action
        self._pending_action = None

        if not confirmed:
            # User cancelled — tell Claude
            self.history.append({
                "role":    "user",
                "content": [{
                    "type":       "tool_result",
                    "tool_use_id": action["tool_id"],
                    "content":    '{"status": "cancelled", "message": "User cancelled this action."}'
                }]
            })
        else:
            # Execute action
            result_msg = _execute_action(action, app_ref)
            self.history.append({
                "role":    "user",
                "content": [{
                    "type":       "tool_result",
                    "tool_use_id": action["tool_id"],
                    "content":    json.dumps(result_msg, ensure_ascii=False)
                }]
            })

        # Get Claude's final response
        final = self.service.send(self.history, use_tools=False)
        if final["type"] in ("text", "error"):
            if final["type"] == "text":
                self.history.append({
                    "role":    "assistant",
                    "content": final["content"]
                })
            return final

        return {"type": "text", "content": "Action processed."}


def result_type_check(loop: int) -> bool:
    """Only stream on first iteration."""
    return loop == 1


def _execute_action(action: dict, app_ref=None) -> dict:
    """Execute a confirmed action via app reference."""
    tool_name = action["tool_name"]
    data      = action["data"]

    try:
        if tool_name == "create_invoice" and app_ref:
            # Switch to billing tab with pre-filled data
            try:
                app_ref.switch_to("billing")
                # Pre-fill customer if billing frame supports it
                bf = app_ref.frames.get("billing")
                if bf and hasattr(bf, "prefill_from_ai"):
                    bf.prefill_from_ai(data)
            except Exception as e:
                return {"status": "partial",
                        "message": f"Switched to billing. Manual entry needed. ({e})"}
            return {
                "status":  "success",
                "message": f"Billing screen opened for {data.get('customer_name','Walk-in')}. "
                           f"Please complete the invoice."
            }

        elif tool_name == "send_whatsapp":
            try:
                import pywhatkit as kit
                from salon_settings import get_settings
                cc = get_settings().get("country_code", "91")
                kit.sendwhatmsg_instantly(
                    f"+{cc}{data['phone']}",
                    data["message"],
                    wait_time=25, tab_close=True)
                return {"status": "success",
                        "message": f"WhatsApp sent to {data['phone']}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        return {"status": "success", "message": "Action completed."}

    except Exception as e:
        return {"status": "error", "message": str(e)}
