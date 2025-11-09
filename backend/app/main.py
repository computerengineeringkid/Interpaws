import time
from datetime import date, timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import Date, cast, text
from sqlalchemy.orm import Session

from . import models, schemas
from .schemas import ChatRequest, ChatResponse, SmartChatRequest, Staff, StaffCreate, BookingUpdate
from .booking_logic import check_availability
from .database import engine, SessionLocal
from .ai_services import get_embedding, get_ollama_recommendation
from .auth import (
    get_password_hash,
    authenticate_client,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI()

@app.on_event("startup")
def on_startup() -> None:
    """Ensure DB is reachable and create vector extension with simple retries.

    This avoids import-time connection attempts and tolerates slow DB startup.
    Tables are now managed by Alembic migrations, not by create_all.
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
            # Tables are now managed by Alembic migrations
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


# ============================================
# Authentication Endpoints
# ============================================

@app.post("/clients/", response_model=schemas.Client, tags=["Authentication"])
def register_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    """Register a new client account."""
    # Check if email already exists
    db_client = db.query(models.Client).filter(models.Client.email == client.email).first()
    if db_client:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new client with hashed password
    hashed_password = get_password_hash(client.password)
    db_client = models.Client(
        name=client.name,
        email=client.email,
        hashed_password=hashed_password,
        clinic_id=client.clinic_id
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint to get an access token."""
    client = authenticate_client(db, form_data.username, form_data.password)
    if not client:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": client.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/clients/me", response_model=schemas.Client, tags=["Authentication"])
async def get_current_client(current_user: models.Client = Depends(get_current_user)):
    """Get the currently authenticated client's details."""
    return current_user


# ============================================
# Booking Endpoints
# ============================================

@app.post("/bookings/", response_model=schemas.Booking)
async def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db)):
    # Check if the staff member is available during the requested time
    is_available = check_availability(db, booking.staff_id, booking.start_time, booking.end_time)
    
    if not is_available:
        raise HTTPException(
            status_code=400,
            detail="Staff member is not available during this time slot."
        )
    
    db_booking = models.Booking(**booking.model_dump())  # type: ignore[arg-type]
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


@app.get("/bookings/me", response_model=List[schemas.Booking], tags=["Bookings"])
async def get_my_bookings(
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bookings for the currently authenticated client."""
    return (
        db.query(models.Booking)
        .filter(models.Booking.client_id == current_user.id)
        .order_by(models.Booking.start_time.desc())
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


# ============================================
# Preferences Endpoints
# ============================================

@app.post("/preferences/me", response_model=schemas.Preferences, tags=["Preferences"])
async def create_my_preferences(
    preferences: schemas.PreferencesCreate,
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update preferences for the currently authenticated client."""
    # Generate embedding for preferences
    details_vector = get_embedding(preferences.details)
    
    # Create new preference record
    db_preferences = models.Preferences(
        details=preferences.details,
        client_id=current_user.id,
        details_vector=details_vector
    )
    db.add(db_preferences)
    db.commit()
    db.refresh(db_preferences)
    return db_preferences


@app.get("/preferences/me", response_model=List[schemas.Preferences], tags=["Preferences"])
async def get_my_preferences(
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all preferences for the currently authenticated client."""
    return (
        db.query(models.Preferences)
        .filter(models.Preferences.client_id == current_user.id)
        .all()
    )


# ============================================
# AI Feedback Loop Endpoints
# ============================================

@app.post("/log-feedback/", response_model=schemas.AIFeedbackLog, tags=["AI Feedback"])
async def log_ai_feedback(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """
    Log successful booking match for AI feedback loop.
    
    This endpoint records when a booking is successfully completed,
    capturing the complaint vector and staff skills vector for future AI training.
    """
    # Fetch the booking
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Fetch the staff member
    staff = db.query(models.Staff).filter(models.Staff.id == booking.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Create feedback log entry
    feedback_log = models.AIFeedbackLog(
        booking_id=booking.id,
        staff_id=staff.id,
        client_complaint_vector=booking.complaint_vector,
        staff_skills_vector=staff.skills_vector
    )
    
    db.add(feedback_log)
    db.commit()
    db.refresh(feedback_log)
    
    return feedback_log
