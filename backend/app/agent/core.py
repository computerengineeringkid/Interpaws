"""Hybrid Agent Core for Interpaws - STABLE VERSION"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from collections import defaultdict
from app.ai_services import extract_json_payload, get_ollama_recommendation
from .tools import AgentTools
from app import models

# Keep track of chat history
CONVERSATION_MEMORY: Dict[str, List[Dict[str, str]]] = defaultdict(list)

class InterpawsAgent:
    def __init__(self, db_session):
        self.tools = AgentTools(db_session)
        self.db = db_session

    async def chat(
        self,
        user_message: str,
        context: str = "",
        session_id: Optional[str] = None,
        prior_history: Optional[List[Dict[str, str]]] = None,
        client_email: Optional[str] = None,
        *,
        complaint_text: Optional[str] = None,
        pet_name: Optional[str] = None,
        owner_name: Optional[str] = None
    ) -> Dict[str, Any]:
        
        # 1. UNDERSTAND: Ask LLM to extract info (Pet Name, Complaint)
        extraction_prompt = f"""
        You are a veterinary receptionist. Extract data from this message: "{user_message}"
        Context: Pet="{pet_name or 'Unknown'}", Complaint="{complaint_text or 'Unknown'}"
        
        Return JSON ONLY:
        {{
            "pet_name": "extracted name or null",
            "complaint": "medical issue or null"
        }}
        """
        raw_response = await get_ollama_recommendation(extraction_prompt, json_mode=True)
        data = extract_json_payload(raw_response) or {}
        
        # 2. UPDATE: Combine new info with what we already knew
        current_pet = data.get("pet_name") or pet_name
        current_complaint = data.get("complaint") or complaint_text
        
        # 3. LOGIC: The "Railroad" - Force specific steps
        
        # Step A: If we don't have a name, ask for it.
        if not current_pet:
            return {
                "response": "I can help with that! First, what is your pet's name?",
                "pet_name": None,
                "owner_name": owner_name
            }
            
        # Step B: If we have a name but no complaint, ask for the issue.
        if not current_complaint:
            return {
                "response": f"Got it, looking up {current_pet}. What seems to be the problem?",
                "pet_name": current_pet,
                "owner_name": owner_name
            }

        # Step C: We have both! Run the tools automatically.
        staff_matches = await self.tools.find_staff(current_complaint)
        if not staff_matches:
             return {
                 "response": "I couldn't find a specialist for that specific issue. Could you describe the symptoms differently?",
                 "pet_name": current_pet,
                 "complaint_text": current_complaint
             }
        
        # Pick the best vet and find their next openings
        best_staff = staff_matches[0]
        staff_obj = self.db.query(models.Staff).filter(models.Staff.id == best_staff['id']).first()
        slots = self.tools._generate_slots(staff=staff_obj, duration_minutes=30)
        
        # Create the response text
        slot_text = "\n".join([f"- {s['start_time'].strftime('%A %I:%M %p')}" for s in slots[:3]])
        response_msg = (
            f"For {current_pet}'s {current_complaint}, I recommend Dr. {best_staff['name']} ({best_staff['role']}).\n"
            f"Available openings:\n{slot_text}\n\n"
            f"Shall I book one?"
        )
        
        return {
            "response": response_msg,
            "slots": slots[:3],
            "pet_name": current_pet,
            "complaint_text": current_complaint
        }