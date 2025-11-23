"""Hybrid Agent Core for Interpaws - BOOKING CAPABLE"""
from __future__ import annotations
import json
from datetime import datetime
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
        
        # Get current time for the LLM to resolve "tomorrow" or "sunday"
        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # 1. UNDERSTAND: Extract Pet, Complaint, AND Booking Intent
        extraction_prompt = f"""
        You are a veterinary receptionist.
        Current Date/Time: {now_str}
        
        User Message: "{user_message}"
        Context: Pet="{pet_name or 'Unknown'}", Complaint="{complaint_text or 'Unknown'}"
        
        Task: Extract fields into JSON.
        - pet_name: Name of the pet (if mentioned).
        - complaint: Medical issue (if mentioned).
        - target_time: If the user is confirming a slot (e.g. "Book Sunday 9am"), convert it to 'YYYY-MM-DD HH:MM' format. If no specific time is chosen, use null.
        
        Return JSON ONLY:
        {{
            "pet_name": "...",
            "complaint": "...",
            "target_time": "2025-11-XX 09:00" or null
        }}
        """
        
        raw_response = await get_ollama_recommendation(extraction_prompt, json_mode=True)
        data = extract_json_payload(raw_response) or {}
        
        # 2. UPDATE STATE
        current_pet = data.get("pet_name") or pet_name
        current_complaint = data.get("complaint") or complaint_text
        target_time = data.get("target_time")
        
        # 3. LOGIC FLOW (The "Railroad")
        
        # Step A: Missing Pet Name
        if not current_pet:
            return {
                "response": "I can help! First, what is your pet's name?",
                "pet_name": None,
                "owner_name": owner_name
            }
            
        # Step B: Missing Complaint
        if not current_complaint:
            return {
                "response": f"Got it, we're checking for {current_pet}. What seems to be the problem?",
                "pet_name": current_pet,
                "owner_name": owner_name
            }

        # Step C: BOOKING (New!) - If we have a time, BOOK IT.
        if target_time:
            # Clean up time string if needed
            booking_result = self.tools.manage_booking(
                pet_name=current_pet,
                owner_name=owner_name or "Client", # Fallback if owner unknown
                complaint_description=current_complaint,
                preferred_time=target_time
            )
            
            if booking_result.get("status") == "success":
                return {
                    "response": booking_result["message"],
                    "service_type": booking_result.get("service_type"),
                    "pet_name": current_pet,
                    "complaint_text": current_complaint
                }
            else:
                # Booking failed (e.g. slot taken), fall through to show slots again
                error_msg = booking_result.get("message", "That slot isn't available.")
                return {
                    "response": f"{error_msg} Here are other available times:",
                    "pet_name": current_pet,
                    "complaint_text": current_complaint
                    # Will fall through to Step D to show slots
                }

        # Step D: Suggestion - Find Staff & Slots
        staff_matches = await self.tools.find_staff(current_complaint)
        if not staff_matches:
             return {
                 "response": "I couldn't find a specialist for that issue. Could you describe it differently?",
                 "pet_name": current_pet,
                 "complaint_text": current_complaint
             }
        
        best_staff = staff_matches[0]
        staff_obj = self.db.query(models.Staff).filter(models.Staff.id == best_staff['id']).first()
        
        # Pass client_id if we had it (requires resolving owner), otherwise generic slots
        # This function already checks client preferences if client_id was passed in a real app
        slots = self.tools._generate_slots(staff=staff_obj, duration_minutes=30)
        
        slot_text = "\n".join([f"- {s['start_time'].strftime('%A %I:%M %p')}" for s in slots[:3]])
        
        response_msg = (
            f"For {current_pet}'s {current_complaint}, I recommend Dr. {best_staff['name']} ({best_staff['role']}).\n"
            f"Available openings:\n{slot_text}\n\n"
            f"Shall I book one? (e.g. 'Yes, Sunday at 9am')"
        )
        
        return {
            "response": response_msg,
            "slots": slots[:3],
            "pet_name": current_pet,
            "complaint_text": current_complaint
        }