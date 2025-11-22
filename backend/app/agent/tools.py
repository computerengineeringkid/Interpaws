"""Action tools for the Interpaws agent."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import Date, cast
from sqlalchemy.orm import Session

from app import models
from app.ai_services import get_embedding
from app.booking_logic import check_availability


class AgentTools:
    """Wrapper around database-backed tools for the agent."""

    def __init__(self, db: Session):
        self.db = db

    def find_staff(self, query: str) -> List[Dict[str, Any]]:
        """Find the top two staff members by semantic similarity to the query."""
        try:
            embedding = get_embedding(query)
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

    def manage_booking(
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
        # 1. Identify Client and Pet
        # Simple case-insensitive match for now
        client = (
            self.db.query(models.Client)
            .filter(models.Client.name.ilike(f"%{owner_name}%"))
            .first()
        )
        if not client:
            return {"status": "error", "message": f"Could not find a client named '{owner_name}'. Please verify the name."}

        pet = (
            self.db.query(models.Pet)
            .filter(models.Pet.client_id == client.id, models.Pet.name.ilike(f"%{pet_name}%"))
            .first()
        )
        if not pet:
            return {"status": "error", "message": f"Could not find a pet named '{pet_name}' for owner '{owner_name}'."}

        # 2. Classify Service & Find Staff
        # We'll use the existing find_staff logic (embedding search)
        # This implicitly handles "Service Classification" by matching complaint to skills
        staff_matches = self.find_staff(complaint_description)
        if not staff_matches:
            return {"status": "error", "message": "No suitable staff found for this complaint."}
        
        best_staff = staff_matches[0]
        staff_id = best_staff["id"]
        staff_name = best_staff["name"]

        # 3. Handle Slot Finding or Booking
        if not preferred_time:
            # Find slots for today/tomorrow
            today_str = datetime.now().strftime("%Y-%m-%d")
            schedule = self.check_schedule(staff_id, today_str)
            return {
                "status": "need_selection",
                "message": f"I found {pet.name}. For '{complaint_description}', {staff_name} is available.",
                "available_slots": schedule.get("available_slots", []),
                "staff_name": staff_name,
                "date": today_str
            }
        else:
            # Try to book
            # preferred_time format expected: "YYYY-MM-DD HH:MM" or similar
            try:
                # Flexible parsing
                try:
                    start_time = datetime.strptime(preferred_time, "%Y-%m-%d %H:%M")
                except ValueError:
                    # Try ISO format
                    start_time = datetime.fromisoformat(preferred_time)

                end_time = start_time + timedelta(hours=1) # Default 1 hour

                # Check availability
                is_available = check_availability(self.db, staff_id, start_time, end_time)
                if not is_available:
                     return {"status": "error", "message": f"Slot {preferred_time} is no longer available."}

                # Create Booking
                new_booking = models.Booking(
                    start_time=start_time,
                    end_time=end_time,
                    client_id=client.id,
                    pet_id=pet.id,
                    staff_id=staff_id,
                    complaint_reason=complaint_description,
                    status="confirmed"
                )
                self.db.add(new_booking)
                self.db.commit()
                self.db.refresh(new_booking)

                return {
                    "status": "success",
                    "message": f"Appointment confirmed for {pet.name} with {staff_name} at {start_time.strftime('%I:%M %p')} on {start_time.strftime('%B %d')}."
                }

            except Exception as e:
                return {"status": "error", "message": f"Booking failed: {str(e)}"}

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
