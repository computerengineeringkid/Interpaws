from datetime import datetime
from sqlalchemy.orm import Session


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
    
    TODO: Implement actual availability logic by checking existing bookings
    """
    return True
