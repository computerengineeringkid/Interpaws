from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import Session
from .models import Booking


def check_availability(db: Session, staff_id: int, start_time: datetime, end_time: datetime) -> bool:
    """
    Check if a staff member is available for a booking in the given time range.
    
    Args:
        db: Database session
        staff_id: ID of the staff member
        start_time: Booking start time
        end_time: Booking end time
    
    Returns:
        True if available, False otherwise
    
    A conflict exists if any booking for this staff member overlaps with the requested time.
    Overlap is defined as: existing.start_time < end_time AND existing.end_time > start_time
    """
    conflicting_booking = (
        db.query(Booking)
        .filter(
            Booking.staff_id == staff_id,
            and_(
                Booking.start_time < end_time,
                Booking.end_time > start_time
            )
        )
        .first()
    )
    
    # Return True if no conflict found (available), False if conflict exists
    return conflicting_booking is None
