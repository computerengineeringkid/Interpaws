"""ReAct-style agent core for Interpaws."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.ai_services import get_ollama_recommendation
from .tools import AgentTools, serialize_tool_output

SYSTEM_PROMPT_TEMPLATE = """
You are the Veterinary Intake Coordinator for Interpaws.
Your goal is to help clients book appointments efficiently via chat.
Today's date and time: {current_date}

Available tools and their required JSON signatures:
- manage_booking: {{"tool": "manage_booking", "args": {{"pet_name": "...", "owner_name": "...", "complaint_description": "...", "preferred_time": "YYYY-MM-DD HH:MM (optional)"}}}}
- propose_slots: {{"tool": "propose_slots", "args": {{"pet_name": "...", "owner_name": "...", "complaint_description": "..."}}}}
- check_inventory: {{"tool": "check_inventory", "args": {{"item_name": "name or partial name"}}}}

Service inference:
- Infer the service type from the complaint BEFORE searching for slots.
- Map vomiting/bleeding/collapse to "urgent care" (60m), vaccines/shots to "vaccination" (30m), annual/checkup to "wellness exam" (45m),
  surgery/lump/spay/neuter to "surgery consult" (60m), dental/teeth to "dental cleaning" (90m), and behavior/anxiety to "behavior consult" (60m).

Protocol:
1. Greet the user and ask how you can help.
2. If the user wants to book, you MUST obtain:
   - Owner's Full Name
   - Pet's Name
   - Reason for visit (Complaint)
3. Do NOT ask the user to select a service type. Infer it from the complaint using the rules above.
4. Use 'propose_slots' or 'manage_booking' WITHOUT 'preferred_time' first to find the correct pet and available slots.
5. Present the available slots to the user.
6. Once the user selects a time, use 'manage_booking' WITH 'preferred_time' to finalize the booking.
7. Always respond with a friendly, professional tone.
8. Output ONLY JSON for tool calls.
"""


class InterpawsAgent:
    """Lightweight ReAct agent with a short tool-use loop."""

    def __init__(self, db_session):
        self.tools = AgentTools(db_session)
        self.max_turns = 3

    async def chat(self, user_message: str, context: str = "") -> Dict[str, Any]:
        history: List[Dict[str, str]] = []
        if context:
            history.append({"role": "system", "content": context})

        current_date = datetime.now().strftime("%A, %B %d, %Y %H:%M")
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date)

        history.append({"role": "system", "content": system_prompt})
        history.append({"role": "user", "content": user_message})

        last_tool_output: Optional[Dict[str, Any]] = None

        for _ in range(self.max_turns):
            prompt = self._format_history(history)
            llm_response = await get_ollama_recommendation(prompt, json_mode=False)
            tool_call = self._parse_tool_call(llm_response)

            if tool_call:
                print(f"Agent Action: {tool_call}")
                tool_result = self._execute_tool(tool_call)
                last_tool_output = tool_result
                print(f"Tool Result: {tool_result}")
                history.append({"role": "assistant", "content": llm_response})
                history.append({"role": "assistant", "content": f"Tool Output: {serialize_tool_output(tool_result)}"})
                continue

            return {"response": llm_response, "tool_output": last_tool_output}

        return {
            "response": "I'm sorry, I couldn't complete your request right now. Please try again later.",
            "tool_output": last_tool_output,
        }

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        conversation = []
        for message in history:
            speaker = message.get("role", "user").capitalize()
            conversation.append(f"{speaker}: {message.get('content', '')}")
        return "\n".join(conversation)

    def _parse_tool_call(self, response_text: str) -> Optional[Dict[str, Any]]:
        if not response_text:
            return None

        try:
            start = response_text.index("{")
            end = response_text.rindex("}") + 1
            candidate = response_text[start:end]
            payload = json.loads(candidate)
        except (ValueError, json.JSONDecodeError):
            return None

        if isinstance(payload, dict) and "tool" in payload and "args" in payload:
            return payload
        return None

    def _execute_tool(self, tool_call: Dict[str, Any]) -> Any:
        tool_name = tool_call.get("tool")
        args = tool_call.get("args", {}) or {}

        if not hasattr(self.tools, tool_name):
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        tool_fn = getattr(self.tools, tool_name)
        try:
            return tool_fn(**args)
        except TypeError:
            return {"status": "error", "message": "Invalid or missing arguments for tool."}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": f"Tool execution failed: {exc}"}
