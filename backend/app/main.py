import time
from datetime import date
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import Date, cast, text
from sqlalchemy.orm import Session

from . import models, schemas
from .schemas import ChatRequest, ChatResponse, SmartChatRequest, Staff, StaffCreate, BookingUpdate
from .booking_logic import check_availability
from .database import engine, SessionLocal
from .ai_services import get_embedding, get_ollama_recommendation

app = FastAPI()

@app.on_event("startup")
def on_startup() -> None:
    """Ensure DB is reachable and create tables with simple retries.

    This avoids import-time connection attempts and tolerates slow DB startup.
    """
    max_attempts = 10
    delay_seconds = 2

    for attempt in range(1, max_attempts + 1):
        try:
            # Try to connect; this ensures the database is up
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                # Create the vector extension
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            # Create tables once connection succeeds
            models.Base.metadata.create_all(bind=engine)
            break
        except Exception:  # noqa: BLE001 - broad to handle transient DB errors
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Interpaws API!"}


def get_db():
    """Provide a database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/bookings/", response_model=schemas.Booking)
async def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    # Check if the staff member is available during the requested time
    is_available = check_availability(db, booking.staff_id, booking.start_time, booking.end_time)
    
    if not is_available:
        raise HTTPException(
            status_code=400,
            detail="Staff member is not available during this time slot."
        )

    # Prepare booking payload
    payload = booking.model_dump()

    # Generate complaint embedding if provided
    complaint_reason = payload.get("complaint_reason")
    complaint_vector = None
    if complaint_reason:
        complaint_vector = get_embedding(complaint_reason)

    db_booking = models.Booking(**payload)  # type: ignore[arg-type]

    # Persist complaint text and vector if available
    if complaint_reason:
        db_booking.complaint_reason = complaint_reason
        db_booking.complaint_vector = complaint_vector

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@app.get("/bookings/{date}", response_model=List[schemas.Booking])
async def get_bookings_for_date(date: date, db: Session = Depends(get_db)):
    return (
        db.query(models.Booking)
        .filter(cast(models.Booking.start_time, Date) == date)
        .all()
    )


@app.post("/suggest_slots", response_model=schemas.SuggestionResponse)
async def get_ai_suggestions(
    request: schemas.SuggestionRequest,
    db: Session = Depends(get_db)
):
    # Get embedding for the complaint text
    complaint_vector = get_embedding(request.complaint_text)
    
    # Perform vector search to find top 3 matching staff members
    # Using the <-> operator for L2 distance in pgvector
    # Only select the columns that exist in the database
    top_staff = (
        db.query(models.Staff.id, models.Staff.name, models.Staff.role)
        .order_by(models.Staff.skills_vector.l2_distance(complaint_vector))
        .limit(3)
        .all()
    )
    
    # Create a formatted prompt for the LLM
    staff_info = "\n".join([
        f"- {staff.name} ({staff.role})"
        for staff in top_staff
    ])
    
    prompt = f"""Given the following pet complaint: "{request.complaint_text}"

We have identified the following staff members as potential matches based on their skills:
{staff_info}

Please explain why these staff members are a good match for this complaint and suggest some potential appointment times for the next week. Be concise and friendly."""
    
    # Get generative recommendation from Ollama
    generative_recommendation = await get_ollama_recommendation(prompt)
    
    # Return the response
    return schemas.SuggestionResponse(
        generative_recommendation=generative_recommendation,
        suggested_staff=[
            schemas.SuggestedStaff(
                id=staff.id,
                name=staff.name,
                role=staff.role
            )
            for staff in top_staff
        ]
    )


@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: SmartChatRequest, db: Session = Depends(get_db)):
    """Smart AI chat endpoint with context from complaint text and staff matching."""
    # Get embedding for the complaint text
    complaint_vector = get_embedding(request.complaint_text)
    
    # Perform vector search to find top 3 matching staff members
    top_staff = (
        db.query(models.Staff.id, models.Staff.name, models.Staff.role)
        .order_by(models.Staff.skills_vector.l2_distance(complaint_vector))
        .limit(3)
        .all()
    )
    
    # Create formatted staff info
    staff_info = "\n".join([
        f"- {staff.name} ({staff.role})"
        for staff in top_staff
    ])
    
    # Create context-aware prompt combining complaint, staff matches, and user's question
    enhanced_prompt = f"""Context:
The pet owner has described the following issue: "{request.complaint_text}"

Based on this complaint, we have identified the following staff members as the best matches:
{staff_info}

User's Question: {request.prompt}

Please answer the user's question using the context provided. Be helpful, friendly, and concise."""
    
    result_text = await get_ollama_recommendation(enhanced_prompt)
    return ChatResponse(response=result_text)


# Staff Endpoints
@app.post("/staff/", response_model=schemas.Staff, tags=["Staff"])
def create_staff(staff: schemas.StaffCreate, db: Session = Depends(get_db)):
    """Create a new staff member."""
    db_staff = models.Staff(name=staff.name, role=staff.role)
    db.add(db_staff)
    db.commit()
    db.refresh(db_staff)
    return db_staff


@app.get("/staff/", response_model=List[schemas.Staff], tags=["Staff"])
def get_all_staff(db: Session = Depends(get_db)):
    """Get all staff members."""
    return db.query(models.Staff).all()


# Booking Management Endpoints
@app.put("/bookings/{booking_id}", response_model=schemas.Booking, tags=["Bookings"])
def update_booking(booking_id: int, booking_update: schemas.BookingUpdate, db: Session = Depends(get_db)):
    """Update an existing booking."""
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Update only the fields that are provided
    update_data = booking_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_booking, field, value)
    
    db.commit()
    db.refresh(db_booking)
    return db_booking


@app.delete("/bookings/{booking_id}", response_model=dict, tags=["Bookings"])
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    """Delete a booking."""
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(db_booking)
    db.commit()
    return {"ok": True}


# Client-specific bookings
@app.get("/bookings/client/{client_id}", response_model=List[schemas.Booking])
def get_client_bookings(client_id: int, db: Session = Depends(get_db)):
    """Return all bookings for a given client."""
    return (
        db.query(models.Booking)
        .filter(models.Booking.client_id == client_id)
        .order_by(models.Booking.start_time.desc())
        .all()
    )


# Preferences Endpoints
@app.post("/preferences/client/{client_id}", response_model=schemas.Preferences)
def create_client_preferences(
    client_id: int,
    preference: schemas.PreferencesCreate,
    db: Session = Depends(get_db),
):
    """Create client preferences with vector embedding for details text."""
    details_vector = get_embedding(preference.details) if preference.details else None

    db_pref = models.Preferences(
        client_id=client_id,
        details=preference.details,
        details_vector=details_vector,
    )
    db.add(db_pref)
    db.commit()
    db.refresh(db_pref)
    return db_pref
