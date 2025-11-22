"""ReAct-style agent core for Interpaws."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

from app.ai_services import extract_json_payload, get_ollama_recommendation
from app.service_catalog import infer_service_type
from .tools import AgentTools, serialize_tool_output

# In-memory conversation storage (in production, use Redis/database)
CONVERSATION_MEMORY: Dict[str, List[Dict[str, str]]] = defaultdict(list)

SYSTEM_PROMPT_TEMPLATE = """Interpaws AI - {current_date}

Smart vet booking assistant. Output JSON.

Tools:
- propose_slots: {{"action": "propose_slots", "action_input": {{"pet_name": "X", "owner_name": "Y", "complaint_description": "Z"}}}}
- find_staff: {{"action": "find_staff", "action_input": {{"query": "text"}}}}
- final_answer: {{"action": "final_answer", "action_input": "text"}}

Rules:
1. Missing info (owner/pet/complaint)? Ask via final_answer
2. Error or ambiguity? Ask user to clarify
3. Can chain tools (find_staff → propose_slots)
4. Urgent symptoms (vomit/bleed) → prioritize urgent care
5. Be conversational and proactive

Memory & Patterns:
- When Client Insights present, mention patterns: "I see you usually book Monday mornings - would that work?"
- Slots are auto-sorted by client's historical preferences
- Build on previous conversation context when session_id provided

Ex - Missing: {{"action": "final_answer", "action_input": "Need your name, pet name, and complaint"}}
Ex - Chain: propose_slots → {{"action": "final_answer", "action_input": "Found urgent care: today 4PM, tomorrow 9AM. Today better - book it?"}}
Ex - Pattern: {{"action": "final_answer", "action_input": "I see you usually book Tuesday afternoons. Would Tuesday 2PM work for Buddy's checkup?"}}
"""


class InterpawsAgent:
    """True ReAct agent with reasoning loop."""

    def __init__(self, db_session):
        self.tools = AgentTools(db_session)
        self.max_turns = 3  # Think → Act → Synthesize

    async def chat(
        self,
        user_message: str,
        context: str = "",
        session_id: Optional[str] = None,
        prior_history: Optional[List[Dict[str, str]]] = None,
        client_email: Optional[str] = None,
        *,
        complaint_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the ReAct reasoning loop with conversation memory."""
        current_date = datetime.now().strftime("%A, %B %d, %Y %H:%M")
        
        # Load conversation history from memory
        conversation_history = []
        if session_id and session_id in CONVERSATION_MEMORY:
            conversation_history = CONVERSATION_MEMORY[session_id].copy()
        elif prior_history:
            conversation_history = prior_history.copy()
        
        # Add pattern insights if available
        pattern_context = ""
        if client_email:
            patterns = self._analyze_client_patterns(client_email)
            if patterns:
                pattern_context = f"\\n\\nUsual: {patterns}"
        
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date) + pattern_context
        
        if context:
            conversation_history.append({"role": "context", "content": context})
        
        conversation_history.append({"role": "system", "content": system_prompt})
        conversation_history.append({"role": "user", "content": user_message})

        complaint_hint = complaint_text or user_message
        
        last_tool_output: Optional[Dict[str, Any]] = None
        
        for turn in range(self.max_turns):
            print(f"\n=== Agent Turn {turn + 1}/{self.max_turns} ===")
            
            # Build prompt from conversation history
            prompt = self._format_history(conversation_history)
            
            # Get LLM response
            llm_response = await get_ollama_recommendation(prompt, json_mode=False)
            print(f"LLM Response: {llm_response[:200]}...")
            
            # Parse the agent's decision
            agent_decision = self._parse_agent_decision(llm_response)
            if not agent_decision:
                agent_decision = await self._retry_agent_decision(prompt)

            if not agent_decision:
                # LLM didn't follow format - fall back to deterministic routing
                fallback = self._keyword_fallback(complaint_hint)
                conversation_history.append({"role": "assistant", "content": fallback["response"]})
                if session_id:
                    self.save_conversation(session_id, conversation_history)
                return fallback
            
            thought = agent_decision.get("thought", "")
            action = agent_decision.get("action", "")
            action_input = agent_decision.get("action_input", {})
            
            if thought:
                print(f"Thought: {thought}")
            print(f"Action: {action}")
            
            # Record this step in history
            thought_str = f"Thought: {thought}\n" if thought else ""
            conversation_history.append({
                "role": "assistant",
                "content": f"{thought_str}Action: {action}\nInput: {json.dumps(action_input)}"
            })
            
            # Handle final answer
            if action == "final_answer":
                final_response = action_input if isinstance(action_input, str) else str(action_input)
                if session_id:
                    self.save_conversation(session_id, conversation_history)
                return {"response": final_response, "tool_output": last_tool_output}
            
            # Execute tool
            if action in ["propose_slots", "manage_booking", "check_schedule", "check_inventory", "find_staff"]:
                tool_result = self._execute_tool(action, action_input)
                last_tool_output = tool_result
                print(f"Tool Result: {tool_result}")
                
                # Add observation to history
                conversation_history.append({
                    "role": "observation",
                    "content": f"Tool '{action}' returned: {serialize_tool_output(tool_result)}"
                })
                
                # Continue loop - agent will see this result and decide next step
                continue
            
            # Unknown action
            return {
                "response": f"I tried to use an unknown action: {action}. Let me try again.",
                "tool_output": last_tool_output
            }
        
        # Max turns reached - synthesize from tool output
        result = self._emergency_synthesis(user_message, last_tool_output)
        if not result.get("response"):
            result = self._keyword_fallback(complaint_hint)
        if session_id:
            conversation_history.append({"role": "assistant", "content": result["response"]})
            self.save_conversation(session_id, conversation_history)
        return result

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history for the LLM."""
        formatted = []
        for entry in history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            
            if role == "system":
                formatted.append(content)
            elif role == "context":
                formatted.append(f"Context: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
            elif role == "observation":
                formatted.append(f"Observation: {content}")
        
        return "\n\n".join(formatted)

    def _parse_agent_decision(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the agent's JSON decision."""
        if not response_text:
            return None

        payload = extract_json_payload(response_text)
        if payload and "action" in payload:
            return payload

        print("JSON parse error: unable to extract action from response")
        return None

    async def _retry_agent_decision(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Retry the LLM with an explicit JSON-only correction prompt."""
        correction_prompt = (
            f"{prompt}\n\nRespond ONLY with a single JSON object containing keys: "
            "action, action_input, and optional thought. No prose or code fences. JSON only."
        )
        retry_response = await get_ollama_recommendation(
            correction_prompt,
            json_mode=False,
            temperature=0.8,
        )
        print(f"Retry response: {retry_response[:200]}...")
        return self._parse_agent_decision(retry_response)

    def _execute_tool(self, tool_name: str, tool_input: Any) -> Any:
        """Execute a tool and return the result."""
        if not hasattr(self.tools, tool_name):
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}
        
        tool_fn = getattr(self.tools, tool_name)
        
        try:
            # Handle different input formats
            if isinstance(tool_input, dict):
                return tool_fn(**tool_input)
            else:
                return tool_fn(tool_input)
        except TypeError as e:
            return {"status": "error", "message": f"Invalid arguments: {str(e)}"}
        except Exception as exc:
            return {"status": "error", "message": f"Tool execution failed: {str(exc)}"}

    def _analyze_client_patterns(self, client_email: str) -> str:
        """Analyze booking patterns for proactive suggestions."""
        try:
            from app import models
            
            client = self.tools.db.query(models.Client).filter(
                models.Client.email == client_email
            ).first()
            
            if not client:
                return ""
            
            # Get last 10 bookings
            bookings = (
                self.tools.db.query(models.Booking)
                .filter(models.Booking.client_id == client.id)
                .order_by(models.Booking.start_time.desc())
                .limit(10)
                .all()
            )
            
            if len(bookings) < 3:
                return ""
            
            insights = []
            
            # Day of week preference
            day_counts = defaultdict(int)
            time_counts = defaultdict(int)
            
            for booking in bookings:
                day_counts[booking.start_time.strftime("%A")] += 1
                hour = booking.start_time.hour
                if hour < 12:
                    time_counts["morning"] += 1
                elif hour < 17:
                    time_counts["afternoon"] += 1
            
            # Most common day
            if day_counts:
                preferred_day = max(day_counts, key=day_counts.get)
                if day_counts[preferred_day] >= 3:
                    insights.append(f"{preferred_day}s")
            
            # Most common time
            if time_counts:
                preferred_time = max(time_counts, key=time_counts.get)
                if time_counts[preferred_time] >= 3:
                    insights.append(f"{preferred_time}")
            
            return ", ".join(insights) if insights else ""
            
        except Exception as e:
            print(f"Pattern analysis error: {e}")
            return ""
    
    def _emergency_synthesis(self, user_message: str, last_tool_output: Optional[Dict]) -> Dict[str, Any]:
        """Emergency fallback when agent hits max turns without final_answer."""
        if last_tool_output and isinstance(last_tool_output, dict):
            status = last_tool_output.get("status")
            
            # Successfully proposed slots
            if status == "need_selection" and last_tool_output.get("slots"):
                slots = last_tool_output.get("slots", [])
                service_type = last_tool_output.get("service_type", "appointment")
                pet_name = last_tool_output.get("pet_name", "your pet")
                
                slot_list = []
                for slot in slots[:3]:
                    start = datetime.fromisoformat(str(slot["start_time"]))
                    slot_list.append(
                        f"- {start.strftime('%A, %B %d at %I:%M %p')} with {slot['staff_name']}"
                    )
                
                response = f"I found {service_type} appointments for {pet_name}:\n\n" + "\n".join(slot_list) + "\n\nWhich time works for you?"
                return {"response": response, "tool_output": last_tool_output}
            
            # Successful booking
            if status == "success":
                return {
                    "response": last_tool_output.get("message", "Booking confirmed!"),
                    "tool_output": last_tool_output
                }
        
        return {
            "response": "I ran into an issue completing that request. Could you try rephrasing?",
            "tool_output": last_tool_output
        }

    def _keyword_fallback(self, complaint_text: str) -> Dict[str, Any]:
        """Deterministic v2-style routing when JSON parsing fails."""
        complaint = complaint_text or ""
        service_type, rationale = infer_service_type(complaint)
        staff_matches = self.tools.find_staff(complaint)
        staff_list = [] if isinstance(staff_matches, dict) else staff_matches
        staff_str = ", ".join([staff.get("name", "staff") for staff in staff_list])
        if not staff_str:
            staff_str = "our on-call veterinary team"

        response = (
            f"I recommend scheduling {service_type} based on what you shared. "
            f"I can route you to {staff_str}. Would you like me to propose the earliest slots?"
        )

        return {
            "response": response,
            "tool_output": {
                "status": "fallback",
                "service_type": service_type,
                "rationale": rationale,
                "staff": staff_list,
            },
        }
    
    def save_conversation(self, session_id: str, conversation_history: List[Dict[str, str]]):
        """Save conversation history to memory."""
        if session_id:
            # Keep last 10 messages to prevent memory bloat
            CONVERSATION_MEMORY[session_id] = conversation_history[-10:]
