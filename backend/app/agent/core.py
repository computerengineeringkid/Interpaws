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

        # Step 1: Store user message in conversation memory
        if session_id:
            CONVERSATION_MEMORY[session_id].append({
                "role": "user",
                "content": user_message
            })

        # Step 2: Retrieve conversation history (last 3 turns = 6 messages)
        history_text = ""
        if session_id and CONVERSATION_MEMORY[session_id]:
            recent_messages = CONVERSATION_MEMORY[session_id][-6:]  # Last 6 messages
            history_lines = []
            for msg in recent_messages:
                role_label = "User" if msg["role"] == "user" else "Agent"
                history_lines.append(f"{role_label}: {msg['content']}")
            history_text = "\n".join(history_lines)

        # 1. UNDERSTAND: Extract Pet, Complaint, AND Booking Intent
        # Build history section for the prompt
        history_section = ""
        if history_text:
            history_section = f"""
        RECENT CONVERSATION HISTORY:
        {history_text}
        """

        extraction_prompt = f"""
        You are an AI Veterinary Assistant. Your goal is to triage the pet's condition safely.
        Current Date/Time: {now_str}

        IMPORTANT: Use the Conversation History to interpret the User Message. If the user answers a previous question (e.g., 'Yes', 'Afternoons', 'I like mornings'), apply it to the current context instead of treating it as a new complaint. For example:
        - If the Agent asked "Do you prefer mornings or afternoons?" and User says "Afternoons", extract time_preference="afternoons"
        - If the Agent asked "Would you like to see the calendar?" and User says "Yes", set request_calendar=true
        - If the Agent asked about a specific day and User confirms, extract the appropriate target_time
        {history_section}
        Context: Pet="{pet_name or 'Unknown'}", Complaint="{complaint_text or 'Unknown'}"

        User Message: "{user_message}"

        Task: Extract medical details. Extract 'pet_species' and 'pet_breed' if mentioned. Infer species from breed (e.g. 'Lab' -> 'Dog', 'Siamese' -> 'Cat'). If the complaint is dangerous (e.g. breathing issues, seizures, bleeding, eating objects), mark 'is_emergency' as true.
        - pet_name: Name of the pet (if mentioned).
        - complaint: Medical issue (if mentioned).
        - target_time: If the user is CONFIRMING/BOOKING a specific slot they chose (e.g. "Book that 2pm slot", "Let's do Tuesday at 3pm"), convert it to 'YYYY-MM-DD HH:MM' format. If no specific time is being BOOKED, use null.
        - check_specific_time: If the user is ASKING about a specific time's availability (e.g. "Do you have 1pm?", "Is 2pm available?", "anything at 3pm?"), extract that time in 'HH:MM' format. Otherwise null.
        - time_preference: Extract general constraints like 'mornings' (before 12pm), 'afternoons' (12-5pm), 'evenings' (after 5pm), 'weekends'. If none, use null.
        - request_calendar: True if user explicitly asks to see the calendar, schedule, or availability (e.g. "show me the calendar", "what's available", "let me see the schedule"), OR if User says "Yes" in response to Agent asking about showing the calendar. Otherwise false.
        - is_question: True if the user is asking for advice, recommendations, or information (e.g., "What should I do?", "Do you recommend any treatment?", "Should I be worried?", "How do I care for my pet?"). False if they're trying to book an appointment.

        Return JSON ONLY:
        {{
            "pet_name": "...",
            "pet_species": "...",
            "pet_breed": "...",
            "complaint": "...",
            "is_emergency": true or false,
            "target_time": "2025-11-XX 09:00" or null,
            "check_specific_time": "13:00" or null,
            "time_preference": "mornings" or null,
            "request_calendar": true or false,
            "is_question": true or false
        }}
        """
        
        raw_response = await get_ollama_recommendation(extraction_prompt, json_mode=True)
        data = extract_json_payload(raw_response) or {}
        
        # 2. UPDATE STATE
        current_pet = data.get("pet_name") or pet_name
        current_complaint = data.get("complaint") or complaint_text
        target_time = data.get("target_time")
        check_specific_time = data.get("check_specific_time")
        current_species = data.get("pet_species")
        current_breed = data.get("pet_breed")
        is_emergency = data.get("is_emergency")
        time_preference = data.get("time_preference")
        request_calendar = data.get("request_calendar", False)
        is_question = data.get("is_question", False)

        # 3. LOGIC FLOW (The "Railroad")

        # Emergency Guard Rail - Check immediately after extraction
        if is_emergency:
            response_payload = {
                "response": "⚠️ This sounds like a medical emergency. Please do not wait for an appointment. Take your pet to the nearest emergency veterinary clinic immediately.",
                "is_emergency": True,
                "pet_name": current_pet,
                "pet_species": current_species,
                "pet_breed": current_breed
            }
            # Store agent response in memory
            if session_id:
                CONVERSATION_MEMORY[session_id].append({
                    "role": "agent",
                    "content": response_payload["response"]
                })
            return response_payload

        # Step A: Missing Pet Name
        if not current_pet:
            response_payload = {
                "response": "I can help! First, what is your pet's name?",
                "pet_name": None,
                "owner_name": owner_name,
                "pet_species": current_species,
                "pet_breed": current_breed
            }
            # Store agent response in memory
            if session_id:
                CONVERSATION_MEMORY[session_id].append({
                    "role": "agent",
                    "content": response_payload["response"]
                })
            return response_payload

        # Step B: Missing Complaint
        if not current_complaint:
            response_payload = {
                "response": f"Got it, we're checking for {current_pet}. What seems to be the problem?",
                "pet_name": current_pet,
                "owner_name": owner_name,
                "pet_species": current_species,
                "pet_breed": current_breed
            }
            # Store agent response in memory
            if session_id:
                CONVERSATION_MEMORY[session_id].append({
                    "role": "agent",
                    "content": response_payload["response"]
                })
            return response_payload

        # Step B.5: Handle Questions/Advice Requests
        # BUT: Check if we've been giving advice repeatedly and the issue persists
        if is_question and current_pet and current_complaint:
            # Check conversation history for repeated advice giving
            advice_count = 0
            if session_id and CONVERSATION_MEMORY[session_id]:
                for msg in CONVERSATION_MEMORY[session_id]:
                    if msg["role"] == "agent" and any(keyword in msg["content"].lower() for keyword in ["try", "recommend", "make sure", "keep", "watch"]):
                        advice_count += 1

            # Check if user is expressing persistence/concern ("still", "ongoing", "keeps", "continues")
            is_persistent = any(word in user_message.lower() for word in ["still", "ongoing", "keeps", "continues", "not working", "persists", "hasn't stopped", "won't stop", "quite a lot", "getting worse"])

            # Check if user is expressing worry or concern
            is_worried = any(word in user_message.lower() for word in ["worried", "concerned", "scared", "afraid", "serious", "bad", "emergency"])

            # If we've given advice 1+ time OR user expresses persistence OR user is worried, transition to booking
            if advice_count >= 1 or is_persistent or is_worried:
                # Skip to booking flow - don't return here, let it fall through to Step D
                pass
            else:
                # Give advice one more time
                advice_prompt = f"""
                You are a helpful veterinary assistant. The pet owner is asking for advice about their pet.

                Pet: {current_pet}
                Issue: {current_complaint}
                Owner's Question: {user_message}

                Provide brief, helpful advice (2-3 sentences). If it's a serious issue or if this is a persistent problem, end by saying: "If the issue persists, I recommend scheduling an appointment with our veterinarian."
                Keep it friendly and reassuring.
                """
                advice_response = await get_ollama_recommendation(advice_prompt)

                response_payload = {
                    "response": advice_response,
                    "pet_name": current_pet,
                    "complaint_text": current_complaint,
                    "pet_species": current_species,
                    "pet_breed": current_breed
                }

                if session_id:
                    CONVERSATION_MEMORY[session_id].append({
                        "role": "agent",
                        "content": advice_response
                    })

                return response_payload

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
                response_payload = {
                    "response": booking_result["message"],
                    "service_type": booking_result.get("service_type"),
                    "pet_name": current_pet,
                    "complaint_text": current_complaint,
                    "pet_species": current_species,
                    "pet_breed": current_breed
                }
                # Store agent response in memory
                if session_id:
                    CONVERSATION_MEMORY[session_id].append({
                        "role": "agent",
                        "content": response_payload["response"]
                    })
                return response_payload
            else:
                error_msg = booking_result.get("message", "That slot isn't available.")
                response_payload = {
                    "response": f"{error_msg} Here are other available times:",
                    "pet_name": current_pet,
                    "complaint_text": current_complaint,
                    "pet_species": current_species,
                    "pet_breed": current_breed
                }
                # Store agent response in memory
                if session_id:
                    CONVERSATION_MEMORY[session_id].append({
                        "role": "agent",
                        "content": response_payload["response"]
                    })
                return response_payload

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

        # 1. Generate a larger pool of slots so we have options to filter
        all_slots = self.tools._generate_slots(staff=staff_obj, duration_minutes=30, max_slots=15)

        # 2. Apply AI-Driven Filtering (The "Control" Layer)
        final_slots = []
        response_intro = ""

        # Check if this is a transition from advice to booking (persistent issue)
        is_persistent_issue = any(word in user_message.lower() for word in ["still", "ongoing", "keeps", "continues", "not working", "persists", "hasn't stopped", "won't stop", "quite a lot", "getting worse"])

        # 2a. Handle persistent issues first - prioritize getting them scheduled
        if is_persistent_issue and not check_specific_time and not time_preference:
            response_intro = f"I understand {current_pet}'s {current_complaint} is ongoing. Let's get you in to see our veterinarian. I recommend Dr. {best_staff['name']} ({best_staff['role']}). Here are their next available appointments:"
            final_slots = all_slots[:3]

        # 2b. Handle specific time checks (e.g., "Do you have 1pm?")
        elif check_specific_time:
            # Parse the requested time (format: "HH:MM" or "H:MM")
            try:
                requested_hour = int(check_specific_time.split(':')[0])
                requested_minute = int(check_specific_time.split(':')[1]) if ':' in check_specific_time else 0

                # Find exact or closest matches
                exact_match = None
                close_matches = []

                for s in all_slots:
                    if s['start_time'].hour == requested_hour and s['start_time'].minute == requested_minute:
                        exact_match = s
                        break
                    # Also collect nearby times (within 1 hour)
                    time_diff = abs((s['start_time'].hour * 60 + s['start_time'].minute) - (requested_hour * 60 + requested_minute))
                    if time_diff <= 120:  # Within 2 hours
                        close_matches.append(s)

                if exact_match:
                    response_intro = f"Yes! I have {check_specific_time} available with Dr. {best_staff['name']}. Would you like to book that time?"
                    final_slots = [exact_match]
                elif close_matches:
                    response_intro = f"I don't have exactly {check_specific_time} available, but I have these nearby times with Dr. {best_staff['name']}:"
                    final_slots = sorted(close_matches, key=lambda x: abs((x['start_time'].hour * 60 + x['start_time'].minute) - (requested_hour * 60 + requested_minute)))[:3]
                else:
                    response_intro = f"Unfortunately, I don't have {check_specific_time} or any nearby times available. Here are the next available slots with Dr. {best_staff['name']}:"
                    final_slots = all_slots[:3]
            except (ValueError, IndexError):
                # If parsing fails, fall back to showing all slots
                response_intro = f"Let me show you what's available with Dr. {best_staff['name']}:"
                final_slots = all_slots[:3]

        elif time_preference:
            time_lower = time_preference.lower()
            for s in all_slots:
                h = s['start_time'].hour
                if "morning" in time_lower and h < 12: final_slots.append(s)
                elif "afternoon" in time_lower and 12 <= h < 17: final_slots.append(s)
                elif "evening" in time_lower and h >= 17: final_slots.append(s)
                elif "weekend" in time_lower and s['start_time'].weekday() >= 5: final_slots.append(s)

            # Intelligent Fallback
            if not final_slots:
                response_intro = f"I checked for **{time_preference}** appointments with Dr. {best_staff['name']}, but those times are fully booked. Here are the closest alternatives:"
                final_slots = all_slots[:3]
            else:
                response_intro = f"Got it! I found these **{time_preference}** openings with Dr. {best_staff['name']} ({best_staff['role']}):"
                final_slots = final_slots[:3]
        else:
            # Standard Triage Response
            species_context = f" ({current_breed} {current_species})" if current_species and current_breed else ""
            response_intro = f"For {current_pet}{species_context} and the concern '{current_complaint}', I recommend Dr. {best_staff['name']} ({best_staff['role']}). Here are their next openings:"
            final_slots = all_slots[:3]

        # 3. Format and Return
        slot_text = "\n".join([f"- {s['start_time'].strftime('%A, %b %d at %I:%M %p')}" for s in final_slots])

        # Memory update for the agent's own context
        response_msg = f"{response_intro}\n\n{slot_text}\n\nShall I book one of these?"

        if session_id:
            CONVERSATION_MEMORY[session_id].append({
                "role": "agent",
                "content": response_msg
            })

        return {
            "response": response_msg,
            "slots": final_slots,
            "pet_name": current_pet,
            "complaint_text": current_complaint
        }