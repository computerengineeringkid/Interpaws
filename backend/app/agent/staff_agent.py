"""
Staff AI Agent - Agentic Architecture with Gemini Function Calling

Gemini is the brain. It decides what to do based on conversation context.
Tools are available for Gemini to call when needed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.genai import types
from sqlalchemy.orm import Session

from app import models
from app.ai_services import agentic_chat, AgenticResponse
from .staff_tools import StaffAgentTools

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT - Gives Gemini full context for staff operations
# =============================================================================

STAFF_SYSTEM_PROMPT = """You are an AI assistant for veterinary clinic staff at Interpaws Veterinary Clinic.

## YOUR ROLE
You are a clinical assistant helping veterinary staff with daily operations. You have access to tools that you MUST use to complete tasks - never just give generic advice.

## CRITICAL: ALWAYS USE YOUR TOOLS - YOU HAVE FULL ACCESS TO EVERYTHING
When staff ask about:
- **Symptoms/health concerns** → ALWAYS call `assess_triage`
- **Schedule/appointments** → Call `get_my_schedule` or `get_all_bookings`
- **Patient/pet information** → Call `search_patient`
- **Medication/inventory** → Call `check_inventory` or `get_low_stock_alerts`
- **Statistics/analytics** → Call `get_analytics` or `get_dashboard_stats`
- **Booking for a client** → Call `book_for_client`
- **Staff workload/busiest** → Call `get_staff_workload`
- **List all staff** → Call `get_all_staff`
- **Reschedule appointments** → Call `reschedule_booking`
- **Client information** → Call `get_client_info`
- **Client preferences** → Call `get_client_preferences`
- **Surgery schedule** → Call `get_surgeries`
- **Schedule new surgery** → Call `schedule_surgery`
- **Visit history** → Call `get_visit_history`
- **Cancel appointments** → Call `cancel_booking`
- **Update inventory** → Call `update_inventory`
- **Register new client** → Call `register_client`
- **Add new pet** → Call `add_pet`
- **Update pet info** → Call `update_pet_info`
- **Update appointment notes** → Call `update_booking_notes`

DO NOT give generic advice. USE THE TOOLS to provide data-driven responses.

## TRIAGE ASSESSMENT GUIDELINES
When staff describe symptoms, ALWAYS use the `assess_triage` tool. Your response should include:
1. **Urgency Level**: EMERGENCY, URGENT, SOON, or ROUTINE
2. **Urgency Score**: Numerical assessment from the tool
3. **Clinical Reasoning**: Why this urgency level
4. **Recommended Action**: What to do next

## URGENCY LEVELS
- **EMERGENCY** (Score 8-10): Life-threatening, immediate intervention needed
- **URGENT** (Score 6-7): Serious, should be seen same-day
- **SOON** (Score 4-5): Should be seen within 24-48 hours
- **ROUTINE** (Score 1-3): Can wait for regular appointment

## RESPONSE STYLE
- Be concise and clinical - staff are busy
- Format information clearly with bullet points
- Always suggest next actions

## CURRENT CONTEXT
Staff member: {staff_name} ({staff_role})
Today's date and time: {current_datetime}
"""

# =============================================================================
# TOOL DEFINITIONS FOR GEMINI
# =============================================================================

def get_staff_tools() -> List[types.Tool]:
    """Define the tools available to the staff agent."""
    return [
        types.Tool(function_declarations=[
            # Schedule tools
            types.FunctionDeclaration(
                name="get_my_schedule",
                description="Get your personal schedule/appointments for a specific date. Use this when the staff member asks about their own schedule.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "date": types.Schema(
                            type=types.Type.STRING,
                            description="Date to check. Use 'today', 'tomorrow', or a date like 'Monday' or '2024-01-15'"
                        )
                    },
                    required=["date"]
                )
            ),
            types.FunctionDeclaration(
                name="get_all_bookings",
                description="Get all clinic bookings/appointments for a specific date. Use this when asking about the entire clinic's schedule.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "date": types.Schema(
                            type=types.Type.STRING,
                            description="Date to check. Use 'today', 'tomorrow', or a specific date"
                        )
                    },
                    required=["date"]
                )
            ),

            # Patient lookup tools
            types.FunctionDeclaration(
                name="search_patient",
                description="Search for a pet/patient by name and/or owner name. Use this to find patient information.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet to search for"
                        ),
                        "owner_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the owner to search for"
                        )
                    }
                )
            ),

            # Inventory tools
            types.FunctionDeclaration(
                name="check_inventory",
                description="Check medication stock levels. Can check a specific medication or get overall inventory status.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "medication_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of specific medication to check (optional - leave empty for full inventory)"
                        )
                    }
                )
            ),
            types.FunctionDeclaration(
                name="get_low_stock_alerts",
                description="Get all medications that are low in stock or out of stock. Use this to check what needs reordering.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),

            # Triage tool
            types.FunctionDeclaration(
                name="assess_triage",
                description="Assess the urgency of reported symptoms. Returns urgency level, score, and recommended action.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "symptoms": types.Schema(
                            type=types.Type.STRING,
                            description="Description of the pet's symptoms"
                        ),
                        "species": types.Schema(
                            type=types.Type.STRING,
                            description="Type of animal (dog, cat, bird, etc.)"
                        )
                    },
                    required=["symptoms"]
                )
            ),

            # Analytics tool
            types.FunctionDeclaration(
                name="get_analytics",
                description="Get booking statistics and analytics. Shows appointment counts, cancellation rates, busiest times.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "period": types.Schema(
                            type=types.Type.STRING,
                            description="Time period: 'today', 'week', or 'month'"
                        )
                    },
                    required=["period"]
                )
            ),

            # Admin booking tool
            types.FunctionDeclaration(
                name="book_for_client",
                description="Book an appointment on behalf of a client. Use this when staff needs to schedule an appointment for a client.",
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
                        "preferred_time": types.Schema(
                            type=types.Type.STRING,
                            description="Preferred appointment time (optional - if not provided, will show available slots)"
                        )
                    },
                    required=["pet_name", "owner_name", "complaint"]
                )
            ),

            # Visit history tool
            types.FunctionDeclaration(
                name="get_visit_history",
                description="Get the visit/appointment history for a specific pet. Use this to view past appointments, treatments, and reasons for visits.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the pet"
                        ),
                        "owner_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the owner (optional, helps narrow down search)"
                        )
                    },
                    required=["pet_name"]
                )
            ),

            # Cancel booking tool
            types.FunctionDeclaration(
                name="cancel_booking",
                description="Cancel an existing appointment. Requires the booking ID or pet name and date.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "booking_id": types.Schema(
                            type=types.Type.INTEGER,
                            description="The booking ID to cancel"
                        ),
                        "pet_name": types.Schema(
                            type=types.Type.STRING,
                            description="Pet name (if booking ID not known)"
                        ),
                        "date": types.Schema(
                            type=types.Type.STRING,
                            description="Date of the appointment to cancel"
                        )
                    }
                )
            ),

            # Update inventory tool
            types.FunctionDeclaration(
                name="update_inventory",
                description="Update medication stock levels. Use this to add or remove stock.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "medication_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the medication"
                        ),
                        "quantity_change": types.Schema(
                            type=types.Type.INTEGER,
                            description="Amount to add (positive) or remove (negative)"
                        ),
                        "reason": types.Schema(
                            type=types.Type.STRING,
                            description="Reason for the inventory change"
                        )
                    },
                    required=["medication_name", "quantity_change"]
                )
            ),

            # Get surgeries tool
            types.FunctionDeclaration(
                name="get_surgeries",
                description="Get scheduled surgeries for a date or date range.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "date": types.Schema(
                            type=types.Type.STRING,
                            description="Date to check surgeries. Use 'today', 'tomorrow', or a specific date"
                        ),
                        "status": types.Schema(
                            type=types.Type.STRING,
                            description="Filter by status: 'Scheduled', 'In-Progress', 'Completed', or 'all'"
                        )
                    },
                    required=["date"]
                )
            ),

            # Get client info tool
            types.FunctionDeclaration(
                name="get_client_info",
                description="Get detailed information about a client including their pets and contact information.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "client_name": types.Schema(
                            type=types.Type.STRING,
                            description="Name of the client to look up"
                        ),
                        "client_email": types.Schema(
                            type=types.Type.STRING,
                            description="Email of the client (optional)"
                        )
                    },
                    required=["client_name"]
                )
            ),

            # Staff workload tool - WHO IS BUSIEST
            types.FunctionDeclaration(
                name="get_staff_workload",
                description="Get staff workload breakdown showing how many appointments each staff member has. Use this to find the busiest doctor/vet, compare workloads, or see who has capacity.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "date": types.Schema(
                            type=types.Type.STRING,
                            description="Date to check workload. Use 'today', 'tomorrow', or a specific date"
                        )
                    },
                    required=["date"]
                )
            ),

            # Get all staff tool
            types.FunctionDeclaration(
                name="get_all_staff",
                description="Get a list of all staff members with their roles, skills, and today's appointment count.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            ),

            # Reschedule booking tool
            types.FunctionDeclaration(
                name="reschedule_booking",
                description="Reschedule an existing appointment to a new date/time.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "booking_id": types.Schema(
                            type=types.Type.INTEGER,
                            description="The booking ID to reschedule"
                        ),
                        "new_date": types.Schema(
                            type=types.Type.STRING,
                            description="The new date for the appointment"
                        ),
                        "new_time": types.Schema(
                            type=types.Type.STRING,
                            description="The new time for the appointment (optional - keeps same time if not provided)"
                        )
                    },
                    required=["booking_id", "new_date"]
                )
            ),

            # ===== FULL ACCESS TOOLS =====
            types.FunctionDeclaration(
                name="register_client",
                description="Register a new client in the system.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(type=types.Type.STRING, description="Client's full name"),
                        "email": types.Schema(type=types.Type.STRING, description="Client's email"),
                        "password": types.Schema(type=types.Type.STRING, description="Initial password")
                    },
                    required=["name", "email"]
                )
            ),
            types.FunctionDeclaration(
                name="add_pet",
                description="Add a new pet for an existing client.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "client_name": types.Schema(type=types.Type.STRING, description="Owner name"),
                        "pet_name": types.Schema(type=types.Type.STRING, description="Pet name"),
                        "species": types.Schema(type=types.Type.STRING, description="Species"),
                        "breed": types.Schema(type=types.Type.STRING, description="Breed"),
                        "date_of_birth": types.Schema(type=types.Type.STRING, description="DOB")
                    },
                    required=["client_name", "pet_name", "species"]
                )
            ),
            types.FunctionDeclaration(
                name="get_client_preferences",
                description="Get a client's preferences and special notes.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "client_name": types.Schema(type=types.Type.STRING, description="Client name")
                    },
                    required=["client_name"]
                )
            ),
            types.FunctionDeclaration(
                name="update_booking_notes",
                description="Update notes for a booking.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "booking_id": types.Schema(type=types.Type.INTEGER, description="Booking ID"),
                        "notes": types.Schema(type=types.Type.STRING, description="New notes")
                    },
                    required=["booking_id", "notes"]
                )
            ),
            types.FunctionDeclaration(
                name="get_dashboard_stats",
                description="Get clinic dashboard statistics - total clients, pets, appointments, surgeries, low stock.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={})
            ),
            types.FunctionDeclaration(
                name="schedule_surgery",
                description="Schedule a new surgery for a pet.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(type=types.Type.STRING, description="Pet name"),
                        "owner_name": types.Schema(type=types.Type.STRING, description="Owner name"),
                        "surgery_type": types.Schema(type=types.Type.STRING, description="Surgery type"),
                        "date": types.Schema(type=types.Type.STRING, description="Date"),
                        "surgeon_name": types.Schema(type=types.Type.STRING, description="Surgeon"),
                        "notes": types.Schema(type=types.Type.STRING, description="Notes")
                    },
                    required=["pet_name", "owner_name", "surgery_type", "date"]
                )
            ),
            types.FunctionDeclaration(
                name="update_pet_info",
                description="Update a pet's information.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pet_name": types.Schema(type=types.Type.STRING, description="Current pet name"),
                        "owner_name": types.Schema(type=types.Type.STRING, description="Owner name"),
                        "new_name": types.Schema(type=types.Type.STRING, description="New name"),
                        "new_breed": types.Schema(type=types.Type.STRING, description="New breed"),
                        "new_species": types.Schema(type=types.Type.STRING, description="New species"),
                        "new_dob": types.Schema(type=types.Type.STRING, description="New DOB")
                    },
                    required=["pet_name"]
                )
            ),
        ])
    ]


# =============================================================================
# STAFF AGENT CLASS
# =============================================================================

class StaffAgent:
    """Agentic staff assistant powered by Gemini function calling."""

    def __init__(self, db_session: Session, staff_member: models.Staff):
        self.db = db_session
        self.staff = staff_member
        self.tools = StaffAgentTools(db_session, staff_member)

    async def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a staff message and return an appropriate response.

        Returns dict with:
        - response: str (required)
        - data: dict (optional)
        - intent: str (inferred from tools called)
        - suggestions: list[str] (optional)
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = f"staff_{uuid.uuid4().hex[:8]}"

        # Build system prompt with staff context
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        system_prompt = STAFF_SYSTEM_PROMPT.format(
            staff_name=self.staff.name,
            staff_role=self.staff.role,
            current_datetime=current_datetime
        )

        # Run the agentic chat loop
        response = await agentic_chat(
            user_message=user_message,
            session_id=session_id,
            system_prompt=system_prompt,
            tools=get_staff_tools(),
            tool_executor=self._execute_tool,
        )

        # Build response dict for frontend compatibility
        result = {
            "response": response.text,
            "session_id": session_id,
        }

        # Infer intent from tools called
        intent = self._infer_intent(response.tool_calls_made)
        result["intent"] = intent

        # Add data from tool results
        if response.tool_results:
            # Combine all tool results into data
            result["data"] = response.tool_results

        # Generate suggestions based on intent
        result["suggestions"] = self._get_suggestions(intent)

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        try:
            if tool_name == "get_my_schedule":
                return await self.tools.get_my_schedule(
                    args.get("date", "today")
                )

            elif tool_name == "get_all_bookings":
                return await self.tools.get_all_bookings(
                    args.get("date", "today")
                )

            elif tool_name == "search_patient":
                return await self.tools.search_pets(
                    pet_name=args.get("pet_name"),
                    owner_name=args.get("owner_name")
                )

            elif tool_name == "check_inventory":
                medication = args.get("medication_name")
                if medication and medication.lower() not in ["null", "none", ""]:
                    return await self.tools.check_medication_stock(medication)
                else:
                    return await self.tools.check_medication_stock()

            elif tool_name == "get_low_stock_alerts":
                return await self.tools.get_low_stock_alerts()

            elif tool_name == "assess_triage":
                return await self.tools.assess_symptom_urgency(
                    symptoms=args.get("symptoms", ""),
                    species=args.get("species")
                )

            elif tool_name == "get_analytics":
                return await self.tools.get_booking_analytics(
                    period=args.get("period", "week")
                )

            elif tool_name == "book_for_client":
                return await self.tools.book_for_client(
                    pet_name=args.get("pet_name", ""),
                    owner_name=args.get("owner_name", ""),
                    complaint=args.get("complaint", "General checkup"),
                    preferred_time=args.get("preferred_time")
                )

            elif tool_name == "get_visit_history":
                return await self.tools.get_visit_history(
                    pet_name=args.get("pet_name", ""),
                    owner_name=args.get("owner_name")
                )

            elif tool_name == "cancel_booking":
                return await self.tools.cancel_booking(
                    booking_id=args.get("booking_id"),
                    pet_name=args.get("pet_name"),
                    date=args.get("date")
                )

            elif tool_name == "update_inventory":
                return await self.tools.update_inventory(
                    medication_name=args.get("medication_name", ""),
                    quantity_change=args.get("quantity_change", 0),
                    reason=args.get("reason")
                )

            elif tool_name == "get_surgeries":
                return await self.tools.get_surgeries(
                    date_str=args.get("date", "today"),
                    status=args.get("status")
                )

            elif tool_name == "get_client_info":
                return await self.tools.get_client_info(
                    client_name=args.get("client_name", ""),
                    client_email=args.get("client_email")
                )

            elif tool_name == "get_staff_workload":
                return await self.tools.get_staff_workload(
                    date_str=args.get("date", "today")
                )

            elif tool_name == "get_all_staff":
                return await self.tools.get_all_staff()

            elif tool_name == "reschedule_booking":
                return await self.tools.reschedule_booking(
                    booking_id=args.get("booking_id"),
                    new_date=args.get("new_date", ""),
                    new_time=args.get("new_time")
                )

            # ===== FULL ACCESS TOOLS =====
            elif tool_name == "register_client":
                return await self.tools.register_client(
                    name=args.get("name", ""),
                    email=args.get("email", ""),
                    password=args.get("password", "password123")
                )

            elif tool_name == "add_pet":
                return await self.tools.add_pet(
                    client_name=args.get("client_name", ""),
                    pet_name=args.get("pet_name", ""),
                    species=args.get("species", ""),
                    breed=args.get("breed"),
                    date_of_birth=args.get("date_of_birth")
                )

            elif tool_name == "get_client_preferences":
                return await self.tools.get_client_preferences(
                    client_name=args.get("client_name", "")
                )

            elif tool_name == "update_booking_notes":
                return await self.tools.update_booking_notes(
                    booking_id=args.get("booking_id"),
                    notes=args.get("notes", "")
                )

            elif tool_name == "get_dashboard_stats":
                return await self.tools.get_dashboard_stats()

            elif tool_name == "schedule_surgery":
                return await self.tools.schedule_surgery(
                    pet_name=args.get("pet_name", ""),
                    owner_name=args.get("owner_name", ""),
                    surgery_type=args.get("surgery_type", ""),
                    date=args.get("date", ""),
                    surgeon_name=args.get("surgeon_name"),
                    notes=args.get("notes")
                )

            elif tool_name == "update_pet_info":
                return await self.tools.update_pet_info(
                    pet_name=args.get("pet_name", ""),
                    owner_name=args.get("owner_name"),
                    new_name=args.get("new_name"),
                    new_breed=args.get("new_breed"),
                    new_species=args.get("new_species"),
                    new_dob=args.get("new_dob")
                )

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return {"error": str(e)}

    def _infer_intent(self, tool_calls: List[Dict[str, Any]]) -> str:
        """Infer the intent from the tools that were called."""
        if not tool_calls:
            return "general_staff"

        # Map tool names to intents
        tool_to_intent = {
            "get_my_schedule": "schedule_query",
            "get_all_bookings": "schedule_query",
            "search_patient": "patient_lookup",
            "check_inventory": "inventory_check",
            "get_low_stock_alerts": "inventory_check",
            "assess_triage": "triage_assist",
            "get_analytics": "analytics_query",
            "book_for_client": "admin_booking",
            "get_visit_history": "patient_lookup",
            "cancel_booking": "booking_management",
            "update_inventory": "inventory_update",
            "get_surgeries": "surgery_query",
            "get_client_info": "client_lookup",
            "get_staff_workload": "staff_workload",
            "get_all_staff": "staff_lookup",
            "reschedule_booking": "booking_management",
        }

        # Use the first tool called to determine intent
        first_tool = tool_calls[0]["name"]
        return tool_to_intent.get(first_tool, "general_staff")

    def _get_suggestions(self, intent: str) -> List[str]:
        """Get relevant suggestions based on the intent."""
        suggestions_map = {
            "schedule_query": ["View patient details", "Check inventory", "Show analytics"],
            "patient_lookup": ["View visit history", "Book appointment", "Check schedule"],
            "inventory_check": ["Check specific medication", "View schedule", "Show analytics"],
            "triage_assist": ["Book urgent appointment", "Check availability", "View schedule"],
            "analytics_query": ["View monthly stats", "Check today's schedule", "Check inventory"],
            "admin_booking": ["View schedule", "Book another appointment", "Check patient"],
            "general_staff": ["View schedule", "Check inventory", "Search patients"],
            "staff_workload": ["View all staff", "Check schedule", "Show analytics"],
            "staff_lookup": ["Check workload", "View schedule", "Book appointment"],
            "booking_management": ["View schedule", "Search patient", "Check availability"],
        }
        return suggestions_map.get(intent, ["View schedule", "Check inventory"])
