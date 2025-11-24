"""Intent Router for Smart Booking System"""
from typing import Dict, List, Optional
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import OllamaEncoder
from pydantic import BaseModel


class IntentRouter:
    """
    Smart Intent Router for booking system.

    Uses semantic routing to classify user intents and extract structured data.
    """

    def __init__(self):
        """Initialize the intent router with predefined routes"""

        # Define intent routes with example utterances
        self.routes = [
            Route(
                name="book_appointment",
                utterances=[
                    "I want to book an appointment for my dog",
                    "Can I schedule a visit for my cat?",
                    "My pet needs to see a vet",
                    "Book me in for next Tuesday at 3pm",
                    "I'd like to make a reservation",
                    "Can we get an appointment for Fluffy?",
                    "Schedule a checkup for my parrot",
                    "I need to bring my rabbit in",
                ],
            ),
            Route(
                name="check_availability",
                utterances=[
                    "What times are available?",
                    "When can I bring my pet in?",
                    "Do you have any morning slots?",
                    "Show me the calendar",
                    "What's your availability?",
                    "Are you free this weekend?",
                    "Can I see available times?",
                    "When are you open?",
                ],
            ),
            Route(
                name="emergency",
                utterances=[
                    "My dog is bleeding!",
                    "Emergency! My cat can't breathe",
                    "My pet is having a seizure",
                    "Help! My dog ate chocolate",
                    "My cat is choking",
                    "Urgent - my pet is unconscious",
                    "My dog was hit by a car",
                    "My pet is vomiting blood",
                ],
            ),
            Route(
                name="cancel_booking",
                utterances=[
                    "I need to cancel my appointment",
                    "Can I cancel Tuesday's booking?",
                    "I want to cancel my reservation",
                    "Cancel my appointment please",
                    "I can't make it anymore",
                    "Need to cancel",
                ],
            ),
            Route(
                name="reschedule_booking",
                utterances=[
                    "Can I reschedule my appointment?",
                    "I need to move my booking to another day",
                    "Change my appointment time",
                    "Reschedule to next week",
                    "Can we move this to Friday?",
                    "I need a different time",
                ],
            ),
            Route(
                name="general_inquiry",
                utterances=[
                    "What services do you offer?",
                    "How much does a checkup cost?",
                    "Where are you located?",
                    "What are your hours?",
                    "Do you treat exotic pets?",
                    "Tell me about your clinic",
                ],
            ),
        ]

        # Initialize encoder (will be set up async)
        self.encoder = None
        self.router = None

    async def initialize(self):
        """Initialize the router asynchronously"""
        if self.router is None:
            # Use Ollama encoder with nomic-embed-text model (default for Interpaws)
            self.encoder = OllamaEncoder(
                model_name="nomic-embed-text",
                host="http://ollama:11434"
            )
            self.router = SemanticRouter(encoder=self.encoder, routes=self.routes)

    async def classify_intent(self, user_message: str) -> Dict[str, any]:
        """
        Classify user intent from message.

        Args:
            user_message: The user's message

        Returns:
            Dict with intent classification:
            {
                "intent": "book_appointment|check_availability|emergency|cancel|reschedule|general",
                "confidence": float,
                "requires_booking": bool
            }
        """
        # Ensure router is initialized
        await self.initialize()

        # Route the message - SemanticRouter returns a Route object or None
        route_choice = self.router(user_message)

        if route_choice is None:
            # Default to general inquiry if no strong match
            return {
                "intent": "general_inquiry",
                "confidence": 0.3,
                "requires_booking": False,
            }

        intent = route_choice.name
        # Confidence is typically high if a route was selected
        confidence = 0.8

        # Determine if this intent requires booking flow
        requires_booking = intent in ["book_appointment", "check_availability", "reschedule_booking"]

        return {
            "intent": intent,
            "confidence": confidence,
            "requires_booking": requires_booking,
        }

    async def extract_booking_details(self, user_message: str, intent: str) -> Dict[str, any]:
        """
        Extract booking-relevant details from message based on intent.

        Args:
            user_message: The user's message
            intent: The classified intent

        Returns:
            Dict with extracted details like pet_name, time_preference, etc.
        """
        from app.ai_services import get_ollama_recommendation, extract_json_payload
        from datetime import datetime

        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

        # Intent-specific extraction prompts
        if intent == "emergency":
            prompt = f"""
            Extract emergency details from: "{user_message}"

            Return JSON:
            {{
                "pet_name": "name or null",
                "pet_species": "species or null",
                "complaint": "emergency issue",
                "is_emergency": true,
                "urgency_level": "critical|high|moderate"
            }}
            """

        elif intent in ["book_appointment", "check_availability"]:
            prompt = f"""
            Current Date/Time: {now_str}

            Extract booking details from: "{user_message}"

            Instructions:
            - Extract pet name, species, breed if mentioned
            - Identify complaint/reason for visit
            - Extract specific time if mentioned (convert to 'YYYY-MM-DD HH:MM')
            - Identify time preferences: 'mornings', 'afternoons', 'evenings', 'weekends'
            - Set request_calendar=true if asking about availability

            Return JSON:
            {{
                "pet_name": "name or null",
                "pet_species": "species or null",
                "pet_breed": "breed or null",
                "complaint": "reason or null",
                "target_time": "YYYY-MM-DD HH:MM or null",
                "time_preference": "mornings|afternoons|evenings|weekends or null",
                "request_calendar": true or false
            }}
            """

        elif intent == "cancel_booking":
            prompt = f"""
            Extract cancellation details from: "{user_message}"

            Return JSON:
            {{
                "pet_name": "name or null",
                "booking_reference": "any mentioned booking ID or time",
                "reason": "cancellation reason or null"
            }}
            """

        elif intent == "reschedule_booking":
            prompt = f"""
            Current Date/Time: {now_str}

            Extract rescheduling details from: "{user_message}"

            Return JSON:
            {{
                "pet_name": "name or null",
                "current_booking_time": "original time if mentioned",
                "new_time": "YYYY-MM-DD HH:MM or null",
                "time_preference": "mornings|afternoons|evenings|weekends or null"
            }}
            """

        else:  # general_inquiry
            prompt = f"""
            Extract any relevant details from: "{user_message}"

            Return JSON:
            {{
                "topic": "main topic of inquiry",
                "pet_species": "if mentioned"
            }}
            """

        # Get LLM extraction
        raw_response = await get_ollama_recommendation(prompt, json_mode=True)
        extracted = extract_json_payload(raw_response) or {}

        return extracted
