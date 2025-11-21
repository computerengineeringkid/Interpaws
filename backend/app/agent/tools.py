"""Action tools for the Interpaws agent."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

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

    def check_schedule(self, staff_id: int, date_str: str, time_str: str) -> Dict[str, str]:
        """Check if a staff member is available at a given date and time."""
        try:
            try:
                start_time = datetime.strptime(
                    f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
                )
            except ValueError:
                start_time = datetime.fromisoformat(f"{date_str} {time_str}")
        except ValueError:
            return {"status": "error", "message": "Invalid date or time format."}

        end_time = start_time + timedelta(minutes=30)
        is_available = check_availability(self.db, staff_id, start_time, end_time)

        return {
            "status": "ok",
            "staff_id": staff_id,
            "slot": start_time.isoformat(),
            "availability": "Available" if is_available else "Busy",
        }

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
