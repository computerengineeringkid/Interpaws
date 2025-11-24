"""Hybrid Agent Core for Interpaws - BOOKING CAPABLE and AWAIT FIXED"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from collections import defaultdict
from app.ai_services import extract_json_payload, get_ollama_recommendation
from .tools import AgentTools
from app import models
from datetime import datetime # Import datetime for target time logic

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
        You are an AI Veterinary Assistant. Your goal is to triage the pet's condition safely.
        Current Date/Time: {now_str}

        User Message: "{user_message}"
        Context: Pet="{pet_name or 'Unknown'}", Complaint="{complaint_text or 'Unknown'}"

        Task: Extract medical details. Extract 'pet_species' and 'pet_breed' if mentioned. Infer species from breed (e.g. 'Lab' -> 'Dog', 'Siamese' -> 'Cat'). If the complaint is dangerous (e.g. breathing issues, seizures, bleeding, eating objects), mark 'is_emergency' as true.
        - pet_name: Name of the pet (if mentioned).
        - complaint: Medical issue (if mentioned).
        - target_time: If the user is confirming a slot (e.g. "Book Sunday 9am"), convert it to 'YYYY-MM-DD HH:MM' format. If no specific time is chosen, use null.
        - time_preference: Extract vague time constraints like "mornings", "after 5pm", "weekends", "next Tuesday", "afternoons". If no preference mentioned, use null.
        - request_calendar: True if user explicitly asks to see the calendar, schedule, or availability (e.g. "show me the calendar", "what's available", "let me see the schedule"). Otherwise false.

        Return JSON ONLY:
        {{
            "pet_name": "...",
            "pet_species": "...",
            "pet_breed": "...",
            "complaint": "...",
            "is_emergency": true or false,
            "target_time": "2025-11-XX 09:00" or null,
            "time_preference": "mornings" or null,
            "request_calendar": true or false
        }}
        """
        
        raw_response = await get_ollama_recommendation(extraction_prompt, json_mode=True)
        data = extract_json_payload(raw_response) or {}
        
        # 2. UPDATE STATE
        current_pet = data.get("pet_name") or pet_name
        current_complaint = data.get("complaint") or complaint_text
        target_time = data.get("target_time")
        current_species = data.get("pet_species")
        current_breed = data.get("pet_breed")
        is_emergency = data.get("is_emergency")
        time_preference = data.get("time_preference")
        request_calendar = data.get("request_calendar", False)

        # 3. LOGIC FLOW (The "Railroad")

        # Emergency Guard Rail - Check immediately after extraction
        if is_emergency:
            return {
                "response": "⚠️ This sounds like a medical emergency. Please do not wait for an appointment. Take your pet to the nearest emergency veterinary clinic immediately.",
                "is_emergency": True,
                "pet_name": current_pet,
                "pet_species": current_species,
                "pet_breed": current_breed
            }

        # Step A: Missing Pet Name
        if not current_pet:
            return {
                "response": "I can help! First, what is your pet's name?",
                "pet_name": None,
                "owner_name": owner_name,
                "pet_species": current_species,
                "pet_breed": current_breed
            }

        # Step B: Missing Complaint
        if not current_complaint:
            return {
                "response": f"Got it, we're checking for {current_pet}. What seems to be the problem?",
                "pet_name": current_pet,
                "owner_name": owner_name,
                "pet_species": current_species,
                "pet_breed": current_breed
            }

        # Step C: BOOKING - If we have a time, BOOK IT.
        if target_time:
            # FIX: Added 'await' here to solve the "cannot unpack non-iterable coroutine object" error
            booking_result = await self.tools.manage_booking( 
                pet_name=current_pet,
                owner_name=owner_name or "Client", 
                complaint_description=current_complaint,
                preferred_time=target_time
            )
            
            if booking_result.get("status") == "success":
                return {
                    "response": booking_result["message"],
                    "service_type": booking_result.get("service_type"),
                    "pet_name": current_pet,
                    "complaint_text": current_complaint,
                    "pet_species": current_species,
                    "pet_breed": current_breed
                }
            else:
                error_msg = booking_result.get("message", "That slot isn't available.")
                return {
                    "response": f"{error_msg} Here are other available times:",
                    "pet_name": current_pet,
                    "complaint_text": current_complaint,
                    "pet_species": current_species,
                    "pet_breed": current_breed
                }

        # Step D: Suggestion - Find Staff & Slots
        staff_matches = await self.tools.find_staff(current_complaint)
        if not staff_matches:
            return {
                "response": "I couldn't find a specialist for that issue. Could you describe it differently?",
                "pet_name": current_pet,
                "complaint_text": current_complaint,
                "pet_species": current_species,
                "pet_breed": current_breed
            }

        best_staff = staff_matches[0]
        staff_obj = self.db.query(models.Staff).filter(models.Staff.id == best_staff['id']).first()

        # Build pet description with species/breed info
        pet_description = current_breed or current_species or "pet"

        # ===== NEGOTIATION STEP =====
        # Condition 1: Explicit Calendar Request
        if request_calendar:
            slots = self.tools._generate_slots(staff=staff_obj, duration_minutes=30)
            return {
                "response": f"Here is the availability calendar for Dr. {best_staff['name']}. Please select a date.",
                "slots": slots[:5],
                "ui_action": "show_calendar",
                "pet_name": current_pet,
                "complaint_text": current_complaint,
                "pet_species": current_species,
                "pet_breed": current_breed
            }

        # Condition 2: No Preferences & No Target Time - Pause to invite input
        if not target_time and not time_preference:
            return {
                "response": f"For {current_pet} (a {pet_description} with {current_complaint}), I recommend Dr. {best_staff['name']} ({best_staff['role']}). Do you have a preference for days or times (e.g., mornings, weekends), or would you like to see the full calendar?",
                "pet_name": current_pet,
                "complaint_text": current_complaint,
                "pet_species": current_species,
                "pet_breed": current_breed
            }

        # Condition 3: Preference Provided - Generate slots with preference context
        slots = self.tools._generate_slots(staff=staff_obj, duration_minutes=30)
        slot_text = "\n".join([f"- {s['start_time'].strftime('%A %I:%M %p')}" for s in slots[:3]])

        if time_preference:
            response_msg = (
                f"I've looked for {time_preference} slots with Dr. {best_staff['name']} for {current_pet}.\n"
                f"Available openings:\n{slot_text}\n\n"
                f"Shall I book one? (e.g., 'Yes, Sunday at 9am')"
            )
        else:
            response_msg = (
                f"For {current_pet} (a {pet_description} with {current_complaint}), I recommend Dr. {best_staff['name']} ({best_staff['role']}).\n"
                f"Available openings:\n{slot_text}\n\n"
                f"Shall I book one? (e.g., 'Yes, Sunday at 9am')"
            )

        return {
            "response": response_msg,
            "slots": slots[:3],
            "pet_name": current_pet,
            "complaint_text": current_complaint,
            "pet_species": current_species,
            "pet_breed": current_breed
        }