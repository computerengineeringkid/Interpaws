"""Action tools for the Interpaws agent."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

from sqlalchemy import Date, cast
from sqlalchemy.orm import Session

from app import models
from app.ai_services import get_embedding
from app.booking_logic import check_availability
from app.service_catalog import get_service_duration_minutes, infer_service_type


class AgentTools:
    """Wrapper around database-backed tools for the agent."""

    def __init__(self, db: Session):
        self.db = db

    async def find_staff(self, query: str) -> List[Dict[str, Any]]:
        """Find the top two staff members by semantic similarity to the query."""
        try:
            embedding = await get_embedding(query)
            staff_results = (
                self.db.query(models.Staff)
                .order_by(models.Staff.skills_vector.l2_distance(embedding))
                .limit(2)
                .all()
            )

            return [
                {"id": staff.id, "name": staff.name, "role": staff.role}
                for staff in staff_results
            ]
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": f"Failed to find staff: {exc}"}

    def _resolve_client_and_pet(self, owner_name: str, pet_name: str) -> Tuple[Any, Any]:
        client_query = (
            self.db.query(models.Client)
            .filter(models.Client.name.ilike(f"%{owner_name}%"))
        )
        clients = client_query.all()
        if not clients:
            return None, {"status": "error", "message": f"Could not find a client named '{owner_name}'. Please ask them to register an account first."}
        if len(clients) > 1:
            return None, {
                "status": "error",
                "message": "Multiple clients match that owner name. Please provide the full name.",
                "candidates": [client.name for client in clients],
            }
        client = clients[0]

        pet_query = (
            self.db.query(models.Pet)
            .filter(models.Pet.client_id == client.id, models.Pet.name.ilike(f"%{pet_name}%"))
        )
        pets = pet_query.all()
        if not pets:
            return None, {"status": "error", "message": f"Could not find a pet named '{pet_name}' for owner '{owner_name}'. Please ask the owner to create this pet profile first."}
        if len(pets) > 1:
            return None, {
                "status": "error",
                "message": "Multiple pets match that name. Please include breed or species to disambiguate.",
                "candidates": [pet.name for pet in pets],
            }

        return client, pets[0]

    async def _infer_service_and_staff(self, complaint_description: str, provided_service: str | None = None) -> Tuple[str, str, List[Dict[str, Any]]]:
        service_type, rationale = infer_service_type(complaint_description, provided_service)
        staff_matches = await self.find_staff(f"{service_type}: {complaint_description}")
        if isinstance(staff_matches, dict):
            return service_type, rationale, []
        return service_type, rationale, staff_matches

    def _generate_slots(
        self,
        staff: models.Staff,
        duration_minutes: int,
        max_slots: int = 3,
        client_id: Optional[int] = None,
        target_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Generate available slots, prioritizing by client's historical patterns.

        If target_date is provided, only returns slots for that specific date.
        Otherwise, searches 14 days ahead (expanded from 5 days).
        """
        from datetime import date as date_type

        now = datetime.utcnow()
        slots: List[Dict[str, Any]] = []

        # If target_date is provided, only search that date
        if target_date:
            # Handle both date and datetime objects
            if isinstance(target_date, date_type) and not isinstance(target_date, datetime):
                search_date = datetime.combine(target_date, datetime.min.time())
            else:
                search_date = target_date
            start_window = search_date
            end_window = search_date + timedelta(days=1)
        else:
            # Default: search 14 days ahead (expanded from 5)
            start_window = now
            end_window = now + timedelta(days=14)

        cursor = start_window

        # Get client preferences if available
        preferred_day = None
        preferred_time = None
        if client_id:
            patterns = self._get_client_patterns(client_id)
            preferred_day = patterns.get("preferred_day")
            preferred_time = patterns.get("preferred_time_period")

        # Collect all available slots first
        all_slots = []
        while cursor < end_window:
            day_start = cursor.replace(hour=9, minute=0, second=0, microsecond=0)
            for hour in range(9, 17):
                start_time = day_start.replace(hour=hour)
                if start_time <= now:
                    continue
                end_time = start_time + timedelta(minutes=duration_minutes)
                if end_time.hour > 17:
                    continue
                if check_availability(self.db, staff.id, start_time, end_time):
                    # Score slot based on client patterns
                    score = 0
                    if preferred_day and start_time.strftime("%A") == preferred_day:
                        score += 10
                    if preferred_time:
                        if preferred_time == "morning" and start_time.hour < 12:
                            score += 5
                        elif preferred_time == "afternoon" and 12 <= start_time.hour < 17:
                            score += 5
                        elif preferred_time == "evening" and start_time.hour >= 17:
                            score += 5

                    all_slots.append({
                        "start_time": start_time,
                        "end_time": end_time,
                        "staff_id": staff.id,
                        "staff_name": staff.name,
                        "score": score
                    })
            cursor += timedelta(days=1)

        # Sort by score (highest first), then by time (earliest first)
        all_slots.sort(key=lambda s: (-s["score"], s["start_time"]))

        # Return top slots
        return all_slots[:max_slots]
    
    def _get_client_patterns(self, client_id: int) -> Dict[str, str]:
        """Extract booking patterns for a client."""
        bookings = (
            self.db.query(models.Booking)
            .filter(models.Booking.client_id == client_id)
            .order_by(models.Booking.start_time.desc())
            .limit(10)
            .all()
        )
        
        if len(bookings) < 3:
            return {}
        
        day_counts = defaultdict(int)
        time_counts = defaultdict(int)
        
        for booking in bookings:
            day_counts[booking.start_time.strftime("%A")] += 1
            hour = booking.start_time.hour
            if hour < 12:
                time_counts["morning"] += 1
            elif hour < 17:
                time_counts["afternoon"] += 1
            else:
                time_counts["evening"] += 1
        
        result = {}
        if day_counts:
            preferred_day = max(day_counts, key=day_counts.get)
            if day_counts[preferred_day] >= 3:
                result["preferred_day"] = preferred_day
        
        if time_counts:
            preferred_time = max(time_counts, key=time_counts.get)
            if time_counts[preferred_time] >= 3:
                result["preferred_time_period"] = preferred_time
        
        return result

    async def propose_slots(self, pet_name: str, owner_name: str, complaint_description: str) -> Dict[str, Any]:
        client, pet_or_error = self._resolve_client_and_pet(owner_name, pet_name)
        if not client:
            return pet_or_error

        service_type, rationale, staff_matches = await self._infer_service_and_staff(complaint_description)
        if not staff_matches:
            return {"status": "error", "message": "No suitable staff found for this complaint."}

        staff_id = staff_matches[0]["id"]
        staff = self.db.query(models.Staff).filter(models.Staff.id == staff_id).first()
        if not staff:
            return {"status": "error", "message": "Selected staff member could not be loaded."}

        duration_minutes = get_service_duration_minutes(service_type)
        slots = self._generate_slots(staff, duration_minutes, client_id=client.id)
        return {
            "status": "need_selection",
            "service_type": service_type,
            "rationale": rationale,
            "slots": slots,
            "pet_name": pet_or_error.name,
            "owner_name": client.name,
            "duration_minutes": duration_minutes,
        }

    def check_schedule(self, staff_id: int, date_str: str, time_str: str = None) -> Dict[str, Any]:
        """Check if a staff member is available at a given date and time."""
        try:
            if time_str:
                # Check specific slot
                try:
                    start_time = datetime.strptime(
                        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    start_time = datetime.fromisoformat(f"{date_str} {time_str}")
                
                end_time = start_time + timedelta(minutes=30)
                is_available = check_availability(self.db, staff_id, start_time, end_time)

                return {
                    "status": "ok",
                    "staff_id": staff_id,
                    "slot": start_time.isoformat(),
                    "availability": "Available" if is_available else "Busy",
                }
            else:
                # Return available slots for the day (simplified 9-5)
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Get existing bookings
                bookings = (
                    self.db.query(models.Booking)
                    .filter(
                        models.Booking.staff_id == staff_id,
                        cast(models.Booking.start_time, Date) == target_date
                    )
                    .all()
                )
                booked_times = [b.start_time.strftime("%H:%M") for b in bookings]
                
                # Simple logic: Assume 9-5 workday, 1 hour slots
                all_slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
                available_slots = [slot for slot in all_slots if slot not in booked_times]
                
                return {
                    "date": date_str,
                    "staff_id": staff_id,
                    "available_slots": available_slots
                }

        except ValueError:
            return {"status": "error", "message": "Invalid date or time format."}
        except Exception as exc:
            return {"status": "error", "message": f"Error checking schedule: {exc}"}

    async def manage_booking(
        self,
        pet_name: str,
        owner_name: str,
        complaint_description: str,
        preferred_time: str = None
    ) -> Dict[str, Any]:
        """
        Unified tool to handle booking flow: identifies pet, classifies service,
        finds staff, and either suggests slots or books the appointment.
        """
        client, pet_or_error = self._resolve_client_and_pet(owner_name, pet_name)
        if not client:
            return pet_or_error

        # Fix: Added 'await' here
        service_type, rationale, staff_matches = await self._infer_service_and_staff(complaint_description)
        if not staff_matches:
            return {"status": "error", "message": "No suitable staff found for this complaint."}

        best_staff = staff_matches[0]
        staff_id = best_staff["id"]
        staff_name = best_staff["name"]
        duration_minutes = get_service_duration_minutes(service_type)

        if not preferred_time:
            staff_obj = self.db.query(models.Staff).filter(models.Staff.id == staff_id).first()
            slots = self._generate_slots(staff_obj, duration_minutes, client_id=client.id)
            return {
                "status": "need_selection",
                "message": f"I found {pet_or_error.name}. For '{complaint_description}', {staff_name} recommends a {service_type} visit. {rationale}",
                "slots": slots,
                "service_type": service_type,
                "duration_minutes": duration_minutes,
            }

        try:
            try:
                start_time = datetime.strptime(preferred_time, "%Y-%m-%d %H:%M")
            except ValueError:
                start_time = datetime.fromisoformat(preferred_time)

            end_time = start_time + timedelta(minutes=duration_minutes)

            is_available = check_availability(self.db, staff_id, start_time, end_time)
            if not is_available:
                return {"status": "error", "message": f"Slot {preferred_time} is no longer available."}

            new_booking = models.Booking(
                start_time=start_time,
                end_time=end_time,
                client_id=client.id,
                pet_id=pet_or_error.id,
                staff_id=staff_id,
                complaint_reason=complaint_description,
                status="confirmed",
            )
            self.db.add(new_booking)
            self.db.commit()
            self.db.refresh(new_booking)

            return {
                "status": "success",
                "message": f"Appointment confirmed for {pet_or_error.name} with {staff_name} at {start_time.strftime('%I:%M %p')} on {start_time.strftime('%B %d')}.",
                "service_type": service_type,
            }

        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": f"Booking failed: {str(exc)}"}

    async def cancel_booking(self, owner_name: str, pet_name: str) -> Dict[str, Any]:
        """Finds the next upcoming booking for the pet and cancels it."""
        client, pet_or_error = self._resolve_client_and_pet(owner_name, pet_name)
        if not client:
            return pet_or_error

        # Find next active booking
        booking = (
            self.db.query(models.Booking)
            .filter(
                models.Booking.pet_id == pet_or_error.id,
                models.Booking.status == "confirmed",
                models.Booking.start_time > datetime.utcnow()
            )
            .order_by(models.Booking.start_time.asc())
            .first()
        )

        if not booking:
            return {"status": "error", "message": f"I couldn't find any upcoming confirmed appointments for {pet_or_error.name}."}

        old_time = booking.start_time.strftime('%A, %B %d at %I:%M %p')
        booking.status = "cancelled"
        self.db.commit()

        return {
            "status": "success",
            "message": f"I have successfully cancelled the appointment for {pet_or_error.name} on {old_time}."
        }

    async def reschedule_booking(self, owner_name: str, pet_name: str, new_time_str: str) -> Dict[str, Any]:
        """Moves the next upcoming booking to a new time."""
        client, pet_or_error = self._resolve_client_and_pet(owner_name, pet_name)
        if not client:
            return pet_or_error

        booking = (
            self.db.query(models.Booking)
            .filter(
                models.Booking.pet_id == pet_or_error.id,
                models.Booking.status == "confirmed",
                models.Booking.start_time > datetime.utcnow()
            )
            .order_by(models.Booking.start_time.asc())
            .first()
        )

        if not booking:
            return {"status": "error", "message": f"I couldn't find an appointment to reschedule for {pet_or_error.name}."}

        # Parse new time
        try:
            try:
                new_start = datetime.strptime(new_time_str, "%Y-%m-%d %H:%M")
            except ValueError:
                new_start = datetime.fromisoformat(new_time_str)

            duration = booking.end_time - booking.start_time
            new_end = new_start + duration

            # Check availability
            if not check_availability(self.db, booking.staff_id, new_start, new_end):
                return {"status": "error", "message": f"The slot at {new_time_str} is not available with Dr. {booking.staff.name}."}

            booking.start_time = new_start
            booking.end_time = new_end
            self.db.commit()

            return {
                "status": "success",
                "message": f"Rescheduled! {pet_or_error.name} is now set for {new_start.strftime('%A, %B %d at %I:%M %p')}."
            }
        except Exception as e:
            return {"status": "error", "message": f"Could not reschedule: {str(e)}"}

    def check_inventory(self, item_name: str) -> Dict[str, Any]:
        """Return the current stock quantity for a medication."""
        medication = (
            self.db.query(models.Medication)
            .filter(models.Medication.name.ilike(f"%{item_name}%"))
            .first()
        )

        if not medication:
            return {"status": "not_found", "item": item_name}

        return {
            "status": "ok",
            "item": medication.name,
            "stock_quantity": medication.stock_quantity,
            "unit": medication.unit,
        }


def serialize_tool_output(output: Any) -> str:
    """Safely serialize tool outputs for the LLM history."""
    try:
        return json.dumps(output)
    except (TypeError, ValueError):
        return str(output)