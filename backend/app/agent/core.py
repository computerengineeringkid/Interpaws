"""ReAct-style agent core for Interpaws."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.ai_services import get_ollama_recommendation
from .tools import AgentTools, serialize_tool_output

SYSTEM_PROMPT = """
You are Interpaws, a veterinary support agent that can reason and use tools.

Available tools and their required JSON signatures:
- find_staff: {"tool": "find_staff", "args": {"query": "skill or complaint description"}}
- check_schedule: {"tool": "check_schedule", "args": {"staff_id": 1, "date_str": "YYYY-MM-DD", "time_str": "HH:MM"}}
- check_inventory: {"tool": "check_inventory", "args": {"item_name": "name or partial name"}}

Rules:
1. When you need factual data about staff, schedules, or inventory, respond with ONLY a JSON object matching the tool format.
2. Do not add any text before or after the JSON when calling a tool. No code fences.
3. Never invent data; rely solely on tool outputs for factual answers.
4. After receiving tool results (they will appear as Tool Output), provide a concise natural language answer.
5. If information is missing, ask the user a brief clarifying question instead of guessing.
"""


class InterpawsAgent:
    """Lightweight ReAct agent with a short tool-use loop."""

    def __init__(self, db_session):
        self.tools = AgentTools(db_session)
        self.max_turns = 3

    async def chat(self, user_message: str, context: str = "") -> str:
        history: List[Dict[str, str]] = []
        if context:
            history.append({"role": "system", "content": context})

        history.append({"role": "system", "content": SYSTEM_PROMPT})
        history.append({"role": "user", "content": user_message})

        for _ in range(self.max_turns):
            prompt = self._format_history(history)
            llm_response = await get_ollama_recommendation(prompt, json_mode=False)
            tool_call = self._parse_tool_call(llm_response)

            if tool_call:
                tool_result = self._execute_tool(tool_call)
                history.append({"role": "assistant", "content": llm_response})
                history.append({"role": "assistant", "content": f"Tool Output: {serialize_tool_output(tool_result)}"})
                continue

            return llm_response

        return "I'm sorry, I couldn't complete your request right now. Please try again later."

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
