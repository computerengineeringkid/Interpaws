"""Enhanced Hybrid Agent with Smart Intent Classification"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from .core import InterpawsAgent, CONVERSATION_MEMORY
from .intent_router import IntentRouter
from app.ai_services import get_ollama_recommendation, extract_json_payload


class EnhancedInterpawsAgent(InterpawsAgent):
    """
    Enhanced version of InterpawsAgent with smart intent classification.

    This agent extends the base InterpawsAgent by adding:
    1. Semantic intent classification using semantic-router
    2. Intent-specific conversation flows
    3. Smarter context understanding
    4. Better handling of complex multi-turn conversations
    """

    def __init__(self, db_session):
        super().__init__(db_session)
        self.intent_router = IntentRouter()
        self._router_initialized = False

    async def _ensure_router_ready(self):
        """Ensure the intent router is initialized"""
        if not self._router_initialized:
            await self.intent_router.initialize()
            self._router_initialized = True

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
        """
        Enhanced chat with intent classification.

        Args:
            user_message: The user's message
            context: Additional context
            session_id: Session ID for conversation memory
            prior_history: Previous conversation history
            client_email: Client's email
            complaint_text: Existing complaint context
            pet_name: Existing pet name context
            owner_name: Owner name context

        Returns:
            Dict with response and metadata
        """

        # Ensure router is ready
        await self._ensure_router_ready()

        # Get current time for the LLM
        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

        # Step 1: Store user message in conversation memory
        if session_id:
            CONVERSATION_MEMORY[session_id].append({
                "role": "user",
                "content": user_message
            })

        # Step 2: Classify Intent using semantic-router
        intent_result = await self.intent_router.classify_intent(user_message)
        detected_intent = intent_result["intent"]
        confidence = intent_result["confidence"]

        print(f"🎯 Intent Classification: {detected_intent} (confidence: {confidence:.2f})")

        # Step 3: Extract details based on intent
        extracted_details = await self.intent_router.extract_booking_details(
            user_message, detected_intent
        )

        # Step 4: Route to appropriate handler based on intent
        if detected_intent == "emergency":
            return await self._handle_emergency(
                extracted_details, session_id, owner_name
            )

        elif detected_intent in ["book_appointment", "check_availability"]:
            return await self._handle_booking_flow(
                user_message=user_message,
                intent=detected_intent,
                extracted_details=extracted_details,
                session_id=session_id,
                pet_name=pet_name,
                owner_name=owner_name,
                complaint_text=complaint_text,
                now_str=now_str
            )

        elif detected_intent == "cancel_booking":
            return await self._handle_cancel_booking(
                extracted_details, session_id, owner_name
            )

        elif detected_intent == "reschedule_booking":
            return await self._handle_reschedule_booking(
                extracted_details, session_id, owner_name
            )

        else:  # general_inquiry or unknown
            return await self._handle_general_inquiry(
                user_message, extracted_details, session_id
            )

    async def _handle_emergency(
        self,
        details: Dict[str, Any],
        session_id: Optional[str],
        owner_name: Optional[str]
    ) -> Dict[str, Any]:
        """Handle emergency situations"""
        pet_name = details.get("pet_name")
        complaint = details.get("complaint", "unknown emergency")

        response = (
            f"⚠️ **EMERGENCY DETECTED** ⚠️\n\n"
            f"This sounds like a medical emergency for {pet_name if pet_name else 'your pet'}. "
            f"**Do NOT wait for an appointment.**\n\n"
            f"Please take your pet to the nearest emergency veterinary clinic immediately.\n\n"
            f"**Emergency Issue:** {complaint}\n\n"
            f"If you need emergency clinic locations, please let me know your area."
        )

        if session_id:
            CONVERSATION_MEMORY[session_id].append({
                "role": "agent",
                "content": response
            })

        return {
            "response": response,
            "is_emergency": True,
            "intent": "emergency",
            "pet_name": pet_name,
            "owner_name": owner_name
        }

    async def _handle_booking_flow(
        self,
        user_message: str,
        intent: str,
        extracted_details: Dict[str, Any],
        session_id: Optional[str],
        pet_name: Optional[str],
        owner_name: Optional[str],
        complaint_text: Optional[str],
        now_str: str
    ) -> Dict[str, Any]:
        """
        Handle booking and availability check intents.
        Falls back to the base agent's proven booking logic.
        """

        # Merge extracted details with existing context
        current_pet = extracted_details.get("pet_name") or pet_name
        current_complaint = extracted_details.get("complaint") or complaint_text
        target_time = extracted_details.get("target_time")
        time_preference = extracted_details.get("time_preference")
        request_calendar = extracted_details.get("request_calendar", False)
        current_species = extracted_details.get("pet_species")
        current_breed = extracted_details.get("pet_breed")

        # If user is asking about availability, provide helpful guidance
        if intent == "check_availability" and request_calendar:
            if not current_pet or not current_complaint:
                response = (
                    "I'd be happy to show you available times! "
                    "First, I need a few details:\n\n"
                )
                if not current_pet:
                    response += "• What's your pet's name?\n"
                if not current_complaint:
                    response += "• What's the reason for the visit?\n"

                if session_id:
                    CONVERSATION_MEMORY[session_id].append({
                        "role": "agent",
                        "content": response
                    })

                return {
                    "response": response,
                    "intent": intent,
                    "pet_name": current_pet,
                    "complaint_text": current_complaint
                }

        # Delegate to base agent's proven booking logic
        # The base agent handles:
        # - Missing pet name/complaint checks
        # - Emergency detection
        # - Booking execution
        # - Staff matching and slot generation
        return await super().chat(
            user_message=user_message,
            context=f"Intent: {intent}. Confidence: {extracted_details}",
            session_id=session_id,
            complaint_text=current_complaint,
            pet_name=current_pet,
            owner_name=owner_name
        )

    async def _handle_cancel_booking(
        self,
        details: Dict[str, Any],
        session_id: Optional[str],
        owner_name: Optional[str]
    ) -> Dict[str, Any]:
        """Handle booking cancellation"""

        pet_name = details.get("pet_name")

        if not pet_name or not owner_name:
            response = "To cancel a booking, I need to know:\n"
            if not pet_name:
                response += "• Which pet's appointment?\n"
            if not owner_name:
                response += "• Your name (account holder)\n"

            if session_id:
                CONVERSATION_MEMORY[session_id].append({
                    "role": "agent",
                    "content": response
                })

            return {
                "response": response,
                "intent": "cancel_booking",
                "status": "need_info"
            }

        # Call the cancel_booking tool
        result = await self.tools.cancel_booking(
            owner_name=owner_name,
            pet_name=pet_name
        )

        response_text = result.get("message", "Booking cancellation processed.")

        if session_id:
            CONVERSATION_MEMORY[session_id].append({
                "role": "agent",
                "content": response_text
            })

        return {
            "response": response_text,
            "intent": "cancel_booking",
            "status": result.get("status", "success")
        }

    async def _handle_reschedule_booking(
        self,
        details: Dict[str, Any],
        session_id: Optional[str],
        owner_name: Optional[str]
    ) -> Dict[str, Any]:
        """Handle booking rescheduling"""

        pet_name = details.get("pet_name")
        new_time = details.get("new_time")

        if not pet_name or not owner_name:
            response = "To reschedule a booking, I need:\n"
            if not pet_name:
                response += "• Which pet's appointment?\n"
            if not owner_name:
                response += "• Your name (account holder)\n"

            if session_id:
                CONVERSATION_MEMORY[session_id].append({
                    "role": "agent",
                    "content": response
                })

            return {
                "response": response,
                "intent": "reschedule_booking",
                "status": "need_info"
            }

        if not new_time:
            response = f"When would you like to reschedule {pet_name}'s appointment? Please provide a date and time (e.g., 'next Monday at 2pm' or '2025-11-28 14:00')."

            if session_id:
                CONVERSATION_MEMORY[session_id].append({
                    "role": "agent",
                    "content": response
                })

            return {
                "response": response,
                "intent": "reschedule_booking",
                "status": "need_time"
            }

        # Call the reschedule_booking tool
        result = await self.tools.reschedule_booking(
            owner_name=owner_name,
            pet_name=pet_name,
            new_time_str=new_time
        )

        response_text = result.get("message", "Booking rescheduled successfully.")

        if session_id:
            CONVERSATION_MEMORY[session_id].append({
                "role": "agent",
                "content": response_text
            })

        return {
            "response": response_text,
            "intent": "reschedule_booking",
            "status": result.get("status", "success")
        }

    async def _handle_general_inquiry(
        self,
        user_message: str,
        details: Dict[str, Any],
        session_id: Optional[str]
    ) -> Dict[str, Any]:
        """Handle general inquiries"""

        # Use LLM to generate helpful response
        prompt = f"""
        You are a friendly veterinary clinic assistant.

        User asked: "{user_message}"

        Topic: {details.get('topic', 'general inquiry')}

        Provide a helpful, friendly response. Keep it concise (2-3 sentences).
        If the user is asking about booking or appointments, guide them to provide:
        - Pet name
        - Reason for visit
        - Preferred time (if any)

        IMPORTANT: Do not invent pet names. If you need to refer to their pet, use 'your pet'.
        """

        response_text = await get_ollama_recommendation(prompt)

        if session_id:
            CONVERSATION_MEMORY[session_id].append({
                "role": "agent",
                "content": response_text
            })

        return {
            "response": response_text,
            "intent": "general_inquiry"
        }
