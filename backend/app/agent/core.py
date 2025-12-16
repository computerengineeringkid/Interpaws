"""
Interpaws Client Agent - Agentic Architecture with Gemini Function Calling

Gemini is the brain. It decides what to do based on conversation context.
Tools are available for Gemini to call when needed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.genai import types
from sqlalchemy.orm import Session

from app import models
from app.ai_services import agentic_chat, AgenticResponse
from app.booking_logic import check_availability
from app.service_catalog import get_service_duration_minutes, infer_service_type
from .tools import AgentTools

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT - Gives Gemini full context and personality
# =============================================================================

CLIENT_SYSTEM_PROMPT = """You are Ivy, a warm and knowledgeable veterinary assistant at Interpaws Veterinary Clinic.

## YOUR PERSONALITY
- Warm and empathetic - you genuinely care about pets and their owners
- Professional but approachable - like a helpful friend at a vet clinic
- Concise - keep responses to 2-4 sentences unless more detail is needed
- Natural - use contractions, be conversational, not robotic

## YOUR CAPABILITIES
You have tools to help clients:
- Look up their pets and information
- Find available appointment slots
- Book, cancel, or reschedule appointments
- Provide health advice using your veterinary knowledge

## EMERGENCY PROTOCOL
For TRUE EMERGENCIES (seizures, difficulty breathing, poisoning, severe bleeding, collapse, trauma):
- DO NOT try to book an appointment
- Immediately direct them to emergency veterinary care
- Say something like: "This sounds like an emergency. Please take [pet name] to the nearest emergency vet clinic immediately. Call ahead if possible."

## CONVERSATION FLOW
1. If a client mentions a health concern, use your knowledge to provide helpful advice
2. If they want to book, ask for pet name if you don't have it
3. Use the tools to find slots and book appointments
4. Be proactive about suggesting appointments for concerning symptoms
5. Remember context from earlier in the conversation

## BOOKING GUIDELINES
- When showing available slots, present 2-3 good options
- Use the pet's name naturally
- Confirm bookings clearly with date, time, and what it's for
- If a requested time isn't available, offer alternatives

## HEALTH ADVICE GUIDELINES
- You can share what symptoms might indicate and home care tips
- Don't diagnose - recommend seeing a vet for diagnosis
- If symptoms are concerning or persistent, recommend booking an appointment
- It's okay to say "I'm not sure" and recommend an appointment

Today's date and time: {current_datetime}
"""

# =============================================================================
# TOOL DEFINITIONS FOR GEMINI
# =============================================================================

def get_client_tools() -> List[types.Tool]:
    """Define the tools available to the client agent."""
    return [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="get_pet_info",
                description="Look up a pet's information including species, breed, age, and owner details. Use this when you need to find information about a client's pet.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="The name of the pet to look up"
                        ),
                        "owner_email": types.Schema(
                            type=types.Type.STRING,
                            description="The owner's email address (optional, helps narrow search)"
                        )
                    },
                    required=["pet_name"]
                )
            ),
            types.FunctionDeclaration(
                name="find_available_slots",
                description="Find available appointment slots for a pet's health concern. Returns a list of available times with the recommended veterinarian.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "complaint": types.Schema(
                            type=types.Type.STRING,
                            description="The health concern or reason for the visit (e.g., 'limping', 'not eating', 'annual checkup')"
                        ),
                        "time_preference": types.Schema(
                            type=types.Type.STRING,
                            description="Optional time preference: 'morning', 'afternoon', 'evening', or 'weekend'"
                        )
                    },
                    required=["complaint"]
                )
            ),
            types.FunctionDeclaration(
                name="book_appointment",
                description="Book a confirmed appointment for a pet. Use this after the client has selected a time slot.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet"
                        ),
                        "owner_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet owner"
                        ),
                        "complaint": types.Schema(
                            type=types.Type.STRING,
                            description="Reason for the visit"
                        ),
                        "appointment_time": types.Schema(
                            type=types.Type.STRING,
                            description="The appointment time in format 'YYYY-MM-DD HH:MM'"
                        )
                    },
                    required=["pet_name", "owner_name", "complaint", "appointment_time"]
                )
            ),
            types.FunctionDeclaration(
                name="cancel_appointment",
                description="Cancel an upcoming appointment for a pet.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet"
                        ),
                        "owner_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet owner"
                        )
                    },
                    required=["pet_name", "owner_name"]
                )
            ),
            types.FunctionDeclaration(
                name="reschedule_appointment",
                description="Reschedule an existing appointment to a new time.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet"
                        ),
                        "owner_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet owner"
                        ),
                        "new_time": types.Schema(
                            type=types.Type.STRING,
                            description="The new appointment time in format 'YYYY-MM-DD HH:MM'"
                        )
                    },
                    required=["pet_name", "owner_name", "new_time"]
                )
            ),
            types.FunctionDeclaration(
                name="get_upcoming_appointments",
                description="Get upcoming appointments for a pet or owner.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet (optional)"
                        ),
                        "owner_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the owner (optional)"
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="get_my_pets",
                description="Get all pets registered to the current client. Use this when the client asks 'what pets do I have?' or 'show me my pets'.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
            types.FunctionDeclaration(
                name="get_clinic_info",
                description="Get clinic information including hours, services, and contact details. Use when clients ask about hours, location, or what services are offered.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),
        ])
    ]


# =============================================================================
# CLIENT AGENT CLASS
# =============================================================================

class InterpawsAgent:
    """Agentic veterinary assistant powered by Gemini function calling."""

    def __init__(self, db_session: Session, client_email: Optional[str] = None):
        self.db = db_session
        self.tools = AgentTools(db_session)
        self.client_email = client_email
        self._owner_name: Optional[str] = None

        # Look up client name if email provided
        if client_email:
            client = self.db.query(models.Client).filter(
                models.Client.email == client_email
            ).first()
            if client:
                self._owner_name = client.name

    async def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        # Legacy params for compatibility
        context: str = "",
        prior_history: Optional[List[Dict[str, str]]] = None,
        client_email: Optional[str] = None,
        complaint_text: Optional[str] = None,
        pet_name: Optional[str] = None,
        owner_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main chat handler - Gemini decides what to do.

        Returns dict with at minimum:
        - response: str (required for frontend)
        - slots: list (optional, for appointment selection)
        - service_type: str (optional)
        - pet_name: str (optional)
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = f"client_{uuid.uuid4().hex[:8]}"

        # Use owner name from lookup or parameter
        effective_owner = owner_name or self._owner_name or "Client"

        # Build system prompt with current datetime
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        system_prompt = CLIENT_SYSTEM_PROMPT.format(current_datetime=current_datetime)

        # Add owner context if known
        if effective_owner and effective_owner != "Client":
            system_prompt += f"\n\nThe current client is: {effective_owner}"
        if pet_name:
            system_prompt += f"\nThey are asking about their pet: {pet_name}"
        if complaint_text:
            system_prompt += f"\nCurrent concern: {complaint_text}"

        # Run the agentic chat loop
        response = await agentic_chat(
            user_message=user_message,
            session_id=session_id,
            system_prompt=system_prompt,
            tools=get_client_tools(),
            tool_executor=lambda name, args: self._execute_tool(name, args, effective_owner),
        )

        # Build response dict for frontend compatibility
        result = {
            "response": response.text,
            "session_id": session_id,
        }

        # Add any slot data from tool results
        if "find_available_slots" in response.tool_results:
            slot_data = response.tool_results["find_available_slots"]
            if isinstance(slot_data, dict):
                result["slots"] = slot_data.get("slots", [])
                result["service_type"] = slot_data.get("service_type")
                result["pet_name"] = slot_data.get("pet_name", pet_name)

        # Add booking confirmation data
        if "book_appointment" in response.tool_results:
            booking_data = response.tool_results["book_appointment"]
            if isinstance(booking_data, dict):
                result["booking_confirmed"] = booking_data.get("status") == "success"
                result["service_type"] = booking_data.get("service_type")

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        owner_name: str
    ) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        try:
            if tool_name == "get_pet_info":
                return await self._tool_get_pet_info(
                    args.get("pet_name", ""),
                    args.get("owner_email")
                )

            elif tool_name == "find_available_slots":
                return await self._tool_find_slots(
                    args.get("complaint", "general checkup"),
                    args.get("time_preference"),
                    owner_name
                )

            elif tool_name == "book_appointment":
                return await self.tools.manage_booking(
                    pet_name=args.get("pet_name", ""),
                    owner_name=args.get("owner_name", owner_name),
                    complaint_description=args.get("complaint", ""),
                    preferred_time=args.get("appointment_time")
                )

            elif tool_name == "cancel_appointment":
                return await self.tools.cancel_booking(
                    owner_name=args.get("owner_name", owner_name),
                    pet_name=args.get("pet_name", "")
                )

            elif tool_name == "reschedule_appointment":
                return await self.tools.reschedule_booking(
                    owner_name=args.get("owner_name", owner_name),
                    pet_name=args.get("pet_name", ""),
                    new_time_str=args.get("new_time", "")
                )

            elif tool_name == "get_upcoming_appointments":
                return await self._tool_get_appointments(
                    args.get("pet_name"),
                    args.get("owner_name", owner_name)
                )

            elif tool_name == "get_my_pets":
                return await self._tool_get_my_pets(owner_name)

            elif tool_name == "get_clinic_info":
                return self._tool_get_clinic_info()

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return {"error": str(e)}

    async def _tool_get_pet_info(
        self,
        pet_name: str,
        owner_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Look up pet information."""
        query = self.db.query(models.Pet).filter(
            models.Pet.name.ilike(f"%{pet_name}%")
        )

        if owner_email:
            query = query.join(models.Client).filter(
                models.Client.email == owner_email
            )

        pets = query.limit(5).all()

        if not pets:
            return {
                "status": "not_found",
                "message": f"No pet named '{pet_name}' found."
            }

        results = []
        for pet in pets:
            owner = self.db.query(models.Client).filter(
                models.Client.id == pet.client_id
            ).first()

            age_str = "Unknown"
            if pet.date_of_birth:
                today = datetime.now().date()
                if pet.date_of_birth <= today:
                    age_delta = today - pet.date_of_birth
                    years = age_delta.days // 365
                    months = (age_delta.days % 365) // 30
                    if years > 0:
                        age_str = f"{years} year{'s' if years != 1 else ''}"
                    else:
                        age_str = f"{months} month{'s' if months != 1 else ''}"

            results.append({
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age": age_str,
                "owner_name": owner.name if owner else "Unknown",
                "owner_email": owner.email if owner else None
            })

        return {
            "status": "success",
            "pets": results,
            "message": f"Found {len(results)} pet(s) named '{pet_name}'"
        }

    async def _tool_find_slots(
        self,
        complaint: str,
        time_preference: Optional[str],
        owner_name: str
    ) -> Dict[str, Any]:
        """Find available appointment slots."""
        # Find best staff for this complaint
        staff_matches = await self.tools.find_staff(complaint)
        if isinstance(staff_matches, dict) and "error" in staff_matches:
            return staff_matches
        if not staff_matches:
            return {"error": "No staff available for this type of appointment."}

        best_staff = staff_matches[0]
        staff = self.db.query(models.Staff).filter(
            models.Staff.id == best_staff["id"]
        ).first()

        if not staff:
            return {"error": "Staff member not found."}

        # Get service type and duration
        service_type, _ = infer_service_type(complaint)
        duration_minutes = get_service_duration_minutes(service_type)

        # Generate slots
        all_slots = self.tools._generate_slots(
            staff=staff,
            duration_minutes=duration_minutes,
            max_slots=10
        )

        # Filter by time preference if specified
        if time_preference:
            pref = time_preference.lower()
            filtered = []
            for slot in all_slots:
                hour = slot["start_time"].hour
                weekday = slot["start_time"].weekday()

                if "morning" in pref and hour < 12:
                    filtered.append(slot)
                elif "afternoon" in pref and 12 <= hour < 17:
                    filtered.append(slot)
                elif "evening" in pref and hour >= 17:
                    filtered.append(slot)
                elif "weekend" in pref and weekday >= 5:
                    filtered.append(slot)

            if filtered:
                all_slots = filtered

        # Format slots for response
        formatted_slots = []
        for slot in all_slots[:5]:
            formatted_slots.append({
                "start_time": slot["start_time"].isoformat(),
                "end_time": slot["end_time"].isoformat(),
                "display": slot["start_time"].strftime("%A, %B %d at %I:%M %p"),
                "staff_name": staff.name,
                "staff_id": staff.id
            })

        return {
            "status": "success",
            "slots": formatted_slots,
            "service_type": service_type,
            "duration_minutes": duration_minutes,
            "recommended_staff": {
                "name": staff.name,
                "role": staff.role
            },
            "message": f"Found {len(formatted_slots)} available slots with {staff.name}"
        }

    async def _tool_get_appointments(
        self,
        pet_name: Optional[str],
        owner_name: str
    ) -> Dict[str, Any]:
        """Get upcoming appointments."""
        query = self.db.query(models.Booking).filter(
            models.Booking.status == "confirmed",
            models.Booking.start_time > datetime.utcnow()
        )

        # Filter by owner
        client = self.db.query(models.Client).filter(
            models.Client.name.ilike(f"%{owner_name}%")
        ).first()

        if client:
            query = query.filter(models.Booking.client_id == client.id)

        # Filter by pet if specified
        if pet_name:
            pet = self.db.query(models.Pet).filter(
                models.Pet.name.ilike(f"%{pet_name}%")
            ).first()
            if pet:
                query = query.filter(models.Booking.pet_id == pet.id)

        bookings = query.order_by(models.Booking.start_time).limit(5).all()

        if not bookings:
            return {
                "status": "none",
                "message": "No upcoming appointments found."
            }

        appointments = []
        for b in bookings:
            pet = self.db.query(models.Pet).filter(models.Pet.id == b.pet_id).first()
            staff = self.db.query(models.Staff).filter(models.Staff.id == b.staff_id).first()

            appointments.append({
                "date": b.start_time.strftime("%A, %B %d"),
                "time": b.start_time.strftime("%I:%M %p"),
                "pet_name": pet.name if pet else "Unknown",
                "reason": b.complaint_reason,
                "with": staff.name if staff else "Staff"
            })

        return {
            "status": "success",
            "appointments": appointments,
            "message": f"Found {len(appointments)} upcoming appointment(s)"
        }

    async def _tool_get_my_pets(self, owner_name: str) -> Dict[str, Any]:
        """Get all pets for the current client."""
        client = self.db.query(models.Client).filter(
            models.Client.name.ilike(f"%{owner_name}%")
        ).first()

        if not client:
            return {"status": "error", "message": "Could not find your account."}

        pets = self.db.query(models.Pet).filter(
            models.Pet.client_id == client.id
        ).all()

        if not pets:
            return {
                "status": "none",
                "message": "You don't have any pets registered yet."
            }

        pet_list = []
        for pet in pets:
            age_str = "Unknown"
            if pet.date_of_birth:
                today = datetime.now().date()
                if pet.date_of_birth <= today:
                    age_delta = today - pet.date_of_birth
                    years = age_delta.days // 365
                    if years > 0:
                        age_str = f"{years} year{'s' if years != 1 else ''} old"
                    else:
                        months = age_delta.days // 30
                        age_str = f"{months} month{'s' if months != 1 else ''} old"

            pet_list.append({
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed or "Unknown",
                "age": age_str
            })

        return {
            "status": "success",
            "pets": pet_list,
            "message": f"You have {len(pet_list)} pet(s) registered."
        }

    def _tool_get_clinic_info(self) -> Dict[str, Any]:
        """Get clinic information."""
        clinic = self.db.query(models.Clinic).first()

        if clinic:
            return {
                "status": "success",
                "name": clinic.name,
                "address": clinic.address,
                "phone": clinic.phone,
                "email": clinic.email,
                "hours": "Monday-Friday: 9:00 AM - 5:00 PM, Saturday: 9:00 AM - 2:00 PM, Sunday: Closed",
                "services": [
                    "Wellness Exams & Vaccinations",
                    "Sick Pet Visits",
                    "Surgery (Spay/Neuter, Dental, Orthopedic)",
                    "Dental Cleanings",
                    "Emergency Care",
                    "Dermatology",
                    "Behavioral Consultations",
                    "Exotic Pet Care"
                ],
                "emergency_note": "For after-hours emergencies, please call our emergency line or visit the nearest 24-hour animal hospital."
            }

        return {
            "status": "success",
            "name": "Interpaws Veterinary Clinic",
            "hours": "Monday-Friday: 9:00 AM - 5:00 PM, Saturday: 9:00 AM - 2:00 PM, Sunday: Closed",
            "services": [
                "Wellness Exams & Vaccinations",
                "Sick Pet Visits",
                "Surgery",
                "Dental Care",
                "Emergency Care"
            ]
        }
