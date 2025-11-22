import json
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import Date, cast, text, func, desc
from sqlalchemy.orm import Session

from . import models, schemas
from .schemas import ChatRequest, ChatResponse, SmartChatRequest, Staff, StaffCreate, StaffUpdate, BookingUpdate
from .booking_logic import check_availability
from .database import engine, SessionLocal
from .ai_services import get_embedding, get_ollama_recommendation
from .agent import InterpawsAgent
from .auth import (
    get_password_hash,
    authenticate_client,
    authenticate_staff,
    create_access_token,
    get_current_user,
    get_current_admin_user,
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


def _clamp_score(value: float) -> float:
    """Keep AI risk scores between 0 and 1."""
    return max(0.0, min(1.0, value))


def _derive_risk_level(score: float) -> str:
    if score >= 0.7:
        return "High"
    if score >= 0.4:
        return "Medium"
    return "Low"


def _extract_json_payload(raw: Optional[str]) -> Optional[dict]:
    """Best-effort JSON extraction so we can recover from LLM formatting drift."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


# ============================================
# Authentication Endpoints
# ============================================

@app.post("/clients", response_model=schemas.Client, tags=["Authentication"])
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


@app.post("/staff/login", response_model=schemas.Token, tags=["Authentication"])
def staff_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Staff login endpoint to get an access token for admin users."""
    staff = authenticate_staff(db, form_data.username, form_data.password)
    if not staff:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": staff.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/clients/me", response_model=schemas.Client, tags=["Authentication"])
async def get_current_client(current_user: models.Client = Depends(get_current_user)):
    """Get the currently authenticated client's details."""
    return current_user


# ============================================
# Booking Endpoints
# ============================================

@app.post("/bookings", response_model=schemas.Booking)
async def create_booking(booking: schemas.BookingCreate, current_user: models.Client = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if the staff member is available during the requested time
    is_available = check_availability(db, booking.staff_id, booking.start_time, booking.end_time)
    
    if not is_available:
        raise HTTPException(
            status_code=400,
            detail="Staff member is not available during this time slot."
        )
    
    db_booking = models.Booking(
        start_time=booking.start_time,
        end_time=booking.end_time,
        client_id=current_user.id,
        pet_id=booking.pet_id,
        staff_id=booking.staff_id
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@app.get("/bookings/{date}", response_model=List[schemas.Booking])
async def get_bookings_for_date(date: date, current_admin: models.Staff = Depends(get_current_admin_user), db: Session = Depends(get_db)):
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


@app.get(
    "/admin/bookings/{booking_id}/risk",
    response_model=schemas.RiskAssessment,
    tags=["Bookings", "Admin", "AI"],
)
async def assess_booking_risk(
    booking_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Analyze historic behavior and have the LLM summarize cancellation risk."""

    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    client = db.query(models.Client).filter(models.Client.id == booking.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found for booking")

    total_bookings = (
        db.query(func.count(models.Booking.id))
        .filter(models.Booking.client_id == client.id)
        .scalar()
    ) or 0

    cancelled_bookings = (
        db.query(func.count(models.Booking.id))
        .filter(
            models.Booking.client_id == client.id,
            models.Booking.status == "cancelled"
        )
        .scalar()
    ) or 0

    cancellation_rate = (cancelled_bookings / total_bookings) if total_bookings else 0.0
    pet = db.query(models.Pet).filter(models.Pet.id == booking.pet_id).first()
    pet_species = pet.species if pet else "Unknown"

    lead_time_days = max(
        0.0,
        (booking.start_time - datetime.utcnow()).total_seconds() / 86400
    )

    booking_type = "Checkup"
    if booking.complaint_reason and "surg" in booking.complaint_reason.lower():
        booking_type = "Surgery"

    prompt = f"""
Client {client.name} has a {booking_type} booking on {booking.start_time:%B %d, %Y}.
History: {cancelled_bookings} cancelled out of {total_bookings} total ({cancellation_rate:.0%}).
Lead time: {lead_time_days:.1f} days. Pet species: {pet_species}.

Instructions:
- If the cancellation rate > 30% or the client has fewer than 2 total bookings, lean toward a higher risk assessment.
- Respond ONLY with valid JSON like {{"risk_score": 0-1 float, "risk_level": "Low|Medium|High", "reasoning": "one sentence"}}.
- Provide a concise reason (< 30 words) referencing the stats above.
"""

    llm_payload = None
    try:
        llm_response = await get_ollama_recommendation(prompt)
        llm_payload = _extract_json_payload(llm_response)
    except Exception:
        llm_payload = None

    if llm_payload:
        try:
            risk_score = _clamp_score(float(llm_payload.get("risk_score", 0.5)))
        except (TypeError, ValueError):
            risk_score = 0.5

        provided_level = (llm_payload.get("risk_level") or "").strip().title()
        if provided_level not in {"Low", "Medium", "High"}:
            provided_level = _derive_risk_level(risk_score)

        reasoning = (llm_payload.get("reasoning") or llm_payload.get("reason") or "").strip()
        if not reasoning:
            reasoning = f"{cancelled_bookings} of {total_bookings} past bookings cancelled."

        return schemas.RiskAssessment(
            risk_score=risk_score,
            risk_level=provided_level,
            reasoning=reasoning
        )

    # Heuristic fallback aligns with the same business rules as the LLM instructions
    short_history_penalty = 0.15 if total_bookings < 2 else 0.0
    rate_factor = cancellation_rate * 0.65
    lead_factor = 0.25 if lead_time_days <= 2 else 0.12 if lead_time_days <= 5 else 0.05
    type_factor = 0.1 if booking_type == "Surgery" else 0.0
    risk_score = _clamp_score(rate_factor + short_history_penalty + lead_factor + type_factor)

    reason_bits = [
        f"Cancellation rate {(cancellation_rate * 100):.0f}%",
        "client history is thin" if total_bookings < 2 else "established client",
    ]

    if lead_time_days <= 2:
        reason_bits.append("short-notice appointment")
    elif booking_type == "Surgery":
        reason_bits.append("surgery anxiety considered")

    return schemas.RiskAssessment(
        risk_score=risk_score,
        risk_level=_derive_risk_level(risk_score),
        reasoning="; ".join(reason_bits)
    )


@app.get(
    "/bookings/{booking_id}/reschedule_options",
    response_model=List[schemas.SuggestedSlot],
    tags=["Bookings"],
)
def get_reschedule_options(
    booking_id: int,
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Surface premium reschedule options tailored to a client's preferences."""

    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to reschedule this booking")

    if not booking.end_time or booking.end_time <= booking.start_time:
        raise HTTPException(status_code=400, detail="Booking duration is invalid")

    duration = booking.end_time - booking.start_time
    now = datetime.utcnow()

    preference = (
        db.query(models.Preferences)
        .filter(models.Preferences.client_id == current_user.id)
        .first()
    )
    preference_vector = None
    if preference and preference.details_vector is not None:
        preference_vector = list(preference.details_vector)

    staff_records = db.query(models.Staff).all()
    if not staff_records:
        return []

    staff_map = {staff.id: staff for staff in staff_records}
    staff_order: List[int] = []
    if booking.staff_id:
        staff_order.append(booking.staff_id)
    staff_order.extend([staff.id for staff in staff_records if staff.id not in staff_order])

    BUSINESS_START_HOUR = 9
    BUSINESS_END_HOUR = 17
    LOOKAHEAD_DAYS = 14
    MAX_CANDIDATES = 15

    candidate_slots = []
    lookahead_end = now + timedelta(days=LOOKAHEAD_DAYS)

    day_cursor = now
    while day_cursor <= lookahead_end and len(candidate_slots) < MAX_CANDIDATES:
        day_start = day_cursor.replace(hour=0, minute=0, second=0, microsecond=0)
        for hour in range(BUSINESS_START_HOUR, BUSINESS_END_HOUR):
            slot_start = day_start.replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot_start <= now:
                continue

            slot_end = slot_start + duration
            if slot_end.date() != slot_start.date():
                continue
            if slot_end.hour > BUSINESS_END_HOUR or (
                slot_end.hour == BUSINESS_END_HOUR and slot_end.minute > 0
            ):
                continue

            for staff_id in staff_order:
                staff = staff_map.get(staff_id)
                if not staff:
                    continue
                if not check_availability(db, staff_id, slot_start, slot_end):
                    continue

                descriptor = f"{slot_start.strftime('%A %I:%M %p')} with {staff.name}"
                preference_match = 0.5
                if preference_vector is not None:
                    slot_embedding = get_embedding(descriptor)
                    distance = sum(
                        (a - b) ** 2
                        for a, b in zip(preference_vector, slot_embedding)
                    ) ** 0.5
                    preference_match = max(0.0, min(1.0, 1 - (distance / 2)))

                continuity_bonus = 0.2 if staff_id == booking.staff_id else 0.0
                days_out = max(0.0, (slot_start - now).total_seconds() / 86400)
                recency_bonus = max(0.0, 1 - (days_out / LOOKAHEAD_DAYS)) * 0.2
                score = preference_match + continuity_bonus + recency_bonus

                reason_bits = []
                if staff_id == booking.staff_id:
                    reason_bits.append("Keeps you with the same care team")
                if preference_match >= 0.65:
                    reason_bits.append("Matches your saved preferences")
                reason_bits.append(slot_start.strftime("%A %I:%M %p"))

                candidate_slots.append({
                    "score": score,
                    "slot": schemas.SuggestedSlot(
                        start_time=slot_start,
                        end_time=slot_end,
                        staff_id=staff_id,
                        staff_name=staff.name,
                        preference_match=round(preference_match, 3),
                        reason=" • ".join(reason_bits)
                    ),
                })

                if len(candidate_slots) >= MAX_CANDIDATES:
                    break
            if len(candidate_slots) >= MAX_CANDIDATES:
                break
        day_cursor += timedelta(days=1)

    if not candidate_slots:
        return []

    candidate_slots.sort(key=lambda item: item["score"], reverse=True)
    top_slots = [entry["slot"] for entry in candidate_slots[:3]]
    return top_slots


@app.put(
    "/bookings/{booking_id}/client_reschedule",
    response_model=schemas.Booking,
    tags=["Bookings"],
)
def client_reschedule_booking(
    booking_id: int,
    request: schemas.ClientRescheduleRequest,
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow clients to apply one-click reschedule options safely."""

    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this booking")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cancelled bookings cannot be rescheduled")

    if request.end_time <= request.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    now = datetime.utcnow()
    if request.start_time <= now:
        raise HTTPException(status_code=400, detail="Rescheduled slot must be in the future")

    original_duration = (booking.end_time - booking.start_time).total_seconds()
    new_duration = (request.end_time - request.start_time).total_seconds()
    if abs(original_duration - new_duration) > 60:
        raise HTTPException(status_code=400, detail="Reschedule duration must match the original appointment")

    new_staff_id = request.staff_id or booking.staff_id
    if not new_staff_id:
        raise HTTPException(status_code=400, detail="A staff member must be specified")

    staff_exists = db.query(models.Staff.id).filter(models.Staff.id == new_staff_id).first()
    if not staff_exists:
        raise HTTPException(status_code=404, detail="Selected staff member was not found")

    if not check_availability(db, new_staff_id, request.start_time, request.end_time):
        raise HTTPException(status_code=400, detail="That slot was just taken. Please pick another option.")

    booking.start_time = request.start_time
    booking.end_time = request.end_time
    booking.staff_id = new_staff_id
    booking.status = "confirmed"

    db.commit()
    db.refresh(booking)
    return booking


@app.post("/suggest_slots", response_model=schemas.SuggestionResponse)
async def get_ai_suggestions(
    request: schemas.SuggestionRequest,
    db: Session = Depends(get_db)
):
    # Get embedding for the complaint text
    complaint_vector = get_embedding(request.complaint_text)
    
    # Query AIFeedbackLog to find "proven staff" from past successful bookings
    # Find staff who have successfully handled similar complaints (L2 distance < 0.5)
    proven_staff_query = (
        db.query(
            models.AIFeedbackLog.staff_id,
            func.count(models.AIFeedbackLog.id).label('match_count')
        )
        .filter(models.AIFeedbackLog.client_complaint_vector.l2_distance(complaint_vector) < 0.5)
        .group_by(models.AIFeedbackLog.staff_id)
        .order_by(desc('match_count'))
        .limit(2)
        .all()
    )
    
    # Get full staff details for proven staff
    proven_staff_ids = [row.staff_id for row in proven_staff_query]
    proven_staff_details = []
    if proven_staff_ids:
        proven_staff_details = (
            db.query(models.Staff.id, models.Staff.name, models.Staff.role)
            .filter(models.Staff.id.in_(proven_staff_ids))
            .all()
        )
    
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
    
    # Build the prompt with both skill-based and proven matches
    prompt = f"""Given the following pet complaint: "{request.complaint_text}"

We have identified the following staff members as potential matches based on their skills:
{staff_info}
"""
    
    # Add proven staff section if we have any
    if proven_staff_details:
        proven_info = "\n".join([
            f"- {staff.name} ({staff.role})"
            for staff in proven_staff_details
        ])
        prompt += f"""
Proven Matches from Past Successes:
{proven_info}

These staff members have successfully handled similar complaints in the past.
"""
    
    prompt += """
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


@app.post("/chat/triage", response_model=ChatResponse, tags=["AI Chat"])
async def triage_chat(request: schemas.SuggestionRequest):
    """
    AI triage endpoint that asks clarifying questions about the user's initial complaint.
    This endpoint initiates an intelligent conversation to gather more details.
    """
    triage_prompt = f"""You are an AI veterinary assistant. A client has entered the following complaint: '{request.complaint_text}'.

Ask one or two clarifying questions to get more details. Consider questions about:
- What breed is your pet?
- How long has this been happening?
- Are there any other symptoms?
- Has your pet experienced this before?
- Is your pet eating and drinking normally?
- Has there been any recent change in behavior or environment?

Be friendly, concise, and professional. Ask the most relevant questions based on the complaint."""
    
    ai_response = await get_ollama_recommendation(triage_prompt)
    return ChatResponse(response=ai_response)


@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: SmartChatRequest, db: Session = Depends(get_db)):
    """Smart AI chat endpoint with context from complaint text and staff matching."""
    # Get embedding for the complaint text
    complaint_vector = get_embedding(request.complaint_text)
    
    # Query AIFeedbackLog to find "proven staff" from past successful bookings
    # Find staff who have successfully handled similar complaints (L2 distance < 0.5)
    proven_staff_query = (
        db.query(
            models.AIFeedbackLog.staff_id,
            func.count(models.AIFeedbackLog.id).label('match_count')
        )
        .filter(models.AIFeedbackLog.client_complaint_vector.l2_distance(complaint_vector) < 0.5)
        .group_by(models.AIFeedbackLog.staff_id)
        .order_by(desc('match_count'))
        .limit(2)
        .all()
    )
    
    # Get full staff details for proven staff
    proven_staff_ids = [row.staff_id for row in proven_staff_query]
    proven_staff_details = []
    if proven_staff_ids:
        proven_staff_details = (
            db.query(models.Staff.id, models.Staff.name, models.Staff.role)
            .filter(models.Staff.id.in_(proven_staff_ids))
            .all()
        )
    
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
"""
    
    # Add proven staff section if we have any
    if proven_staff_details:
        proven_info = "\n".join([
            f"- {staff.name} ({staff.role})"
            for staff in proven_staff_details
        ])
        enhanced_prompt += f"""
Proven Matches from Past Successes:
{proven_info}

These staff members have successfully handled similar complaints in the past.
"""
    
    enhanced_prompt += f"""
User's Question: {request.prompt}

Please answer the user's question using the context provided. Be helpful, friendly, and concise."""
    
    result_text = await get_ollama_recommendation(enhanced_prompt)
    return ChatResponse(response=result_text)


@app.post("/agent/chat", response_model=ChatResponse, tags=["AI Chat"])
async def agent_chat(request: SmartChatRequest, db: Session = Depends(get_db)):
    """Agentic ReAct chat endpoint using tool calls for factual answers."""
    agent = InterpawsAgent(db)
    context = f"User context: complaint details - {request.complaint_text}"
    response_text = await agent.chat(request.prompt, context=context)
    return ChatResponse(response=response_text)


# Staff Endpoints
@app.post("/staff/", response_model=schemas.Staff, tags=["Staff"])
def create_staff(staff: schemas.StaffCreate, current_admin: models.Staff = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Create a new staff member."""
    # Check if email already exists
    db_staff = db.query(models.Staff).filter(models.Staff.email == staff.email).first()
    if db_staff:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate embedding for skills_description if provided
    skills_vector = None
    if staff.skills_description:
        skills_vector = get_embedding(staff.skills_description)
    
    # Create new staff with hashed password
    hashed_password = get_password_hash(staff.password)
    db_staff = models.Staff(
        name=staff.name,
        email=staff.email,
        hashed_password=hashed_password,
        role=staff.role,
        skills_description=staff.skills_description,
        skills_vector=skills_vector
    )
    db.add(db_staff)
    db.commit()
    db.refresh(db_staff)
    return db_staff


@app.get("/staff/", response_model=List[schemas.Staff], tags=["Staff"])
def get_all_staff(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all staff members. Admin only."""
    return db.query(models.Staff).all()


@app.put("/staff/{staff_id}", response_model=schemas.Staff, tags=["Staff"])
def update_staff(
    staff_id: int,
    staff_update: schemas.StaffUpdate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a staff member. Admin only."""
    db_staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    
    if not db_staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Update only the fields that are provided
    update_data = staff_update.model_dump(exclude_unset=True)
    
    # If skills_description is being updated, regenerate the embedding
    if "skills_description" in update_data and update_data["skills_description"] is not None:
        db_staff.skills_vector = get_embedding(update_data["skills_description"])
    
    for field, value in update_data.items():
        setattr(db_staff, field, value)
    
    db.commit()
    db.refresh(db_staff)
    return db_staff


@app.delete("/staff/{staff_id}", response_model=dict, tags=["Staff"])
def delete_staff(
    staff_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a staff member. Admin only."""
    db_staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    
    if not db_staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    db.delete(db_staff)
    db.commit()
    return {"ok": True}


# Booking Management Endpoints
@app.put("/bookings/{booking_id}", response_model=schemas.Booking, tags=["Bookings"])
def update_booking(
    booking_id: int,
    booking_update: schemas.BookingUpdate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update an existing booking. Admin only."""
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
def delete_booking(
    booking_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a booking. Admin only."""
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    db.delete(db_booking)
    db.commit()
    return {"ok": True}


@app.get("/admin/cancellation_suggestion/{booking_id}", 
         response_model=schemas.CancellationSuggestionResponse, 
         tags=["Bookings", "Admin"])
async def get_cancellation_suggestions(
    booking_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get intelligent suggestions for filling a cancelled appointment slot.
    
    Sprint 8: Dynamic Slot-Filling
    
    When a booking is cancelled, this endpoint finds clients with later appointments
    on the same day who might prefer the earlier (now available) slot based on their
    preferences.
    
    Args:
        booking_id: The ID of the cancelled booking
        current_admin: Admin authentication
        db: Database session
        
    Returns:
        CancellationSuggestionResponse with top 3 candidate clients
    """
    # Fetch the cancelled booking
    cancelled_booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id
    ).first()
    
    if not cancelled_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    cancelled_slot_time = cancelled_booking.start_time
    cancelled_date = cancelled_slot_time.date()
    
    # Determine time period of the cancelled slot
    hour = cancelled_slot_time.hour
    if hour < 12:
        time_period = "morning"
        time_description = "morning appointment"
    elif hour < 17:
        time_period = "afternoon"
        time_description = "afternoon appointment"
    else:
        time_period = "evening"
        time_description = "evening appointment"
    
    # Find candidate bookings: same day, later time, not cancelled
    candidate_bookings = (
        db.query(models.Booking)
        .filter(
            models.Booking.id != booking_id,  # Not the cancelled booking itself
            cast(models.Booking.start_time, Date) == cancelled_date,  # Same day
            models.Booking.start_time > cancelled_slot_time,  # Later time
            models.Booking.status != "cancelled"  # Not already cancelled
        )
        .all()
    )
    
    if not candidate_bookings:
        # No candidates found - return empty suggestions
        return schemas.CancellationSuggestionResponse(
            cancelled_slot_time=cancelled_slot_time,
            suggestions=[]
        )
    
    # Generate embedding for "earlier appointment" concept
    earlier_embedding = get_embedding(f"I prefer earlier appointments, especially {time_description}")
    
    suggestions = []
    
    for booking in candidate_bookings:
        # Get client information
        client = db.query(models.Client).filter(
            models.Client.id == booking.client_id
        ).first()
        
        if not client:
            continue
        
        # Get client preferences
        preference = db.query(models.Preferences).filter(
            models.Preferences.client_id == client.id
        ).first()
        
        # Calculate match score
        match_score = 0.5  # Default score
        reason = f"Has appointment at {booking.start_time.strftime('%I:%M %p')}, could move to {cancelled_slot_time.strftime('%I:%M %p')}"
        
        if preference and preference.details_vector is not None:
            # Calculate L2 distance between preference and "earlier appointment" concept
            # Lower distance = better match
            distance = sum(
                (a - b) ** 2 
                for a, b in zip(preference.details_vector, earlier_embedding)
            ) ** 0.5
            
            # Convert distance to score (0-1, where 1 is best match)
            # Normalize: typical L2 distances are 0-2, so we invert and scale
            match_score = max(0, min(1, 1 - (distance / 2)))
            
            # Enhanced reason based on preference text
            if preference.details:
                # Check for preference keywords
                details_lower = preference.details.lower()
                if any(word in details_lower for word in ['morning', 'early', 'am', 'earlier']):
                    reason = f"Prefers {time_period} appointments (currently at {booking.start_time.strftime('%I:%M %p')})"
                elif match_score > 0.7:
                    reason = f"Strong preference match for earlier time (currently at {booking.start_time.strftime('%I:%M %p')})"
        else:
            # No preference vector, use time-based scoring
            # Give higher score to bookings much later in the day
            time_diff_hours = (booking.start_time - cancelled_slot_time).total_seconds() / 3600
            match_score = min(1.0, time_diff_hours / 4)  # Cap at 1.0, scale by 4-hour difference
        
        suggestions.append(
            schemas.CancellationSuggestion(
                client_name=client.name,
                client_email=client.email,
                current_booking_id=booking.id,
                current_booking_time=booking.start_time,
                match_score=match_score,
                reason=reason
            )
        )
    
    # Sort by match score (highest first) and take top 3
    suggestions.sort(key=lambda x: x.match_score, reverse=True)
    top_suggestions = suggestions[:3]
    
    return schemas.CancellationSuggestionResponse(
        cancelled_slot_time=cancelled_slot_time,
        suggestions=top_suggestions
    )


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

@app.post("/log-feedback/", response_model=schemas.AIFeedbackLogResponse, tags=["AI Feedback"])
async def log_ai_feedback(
    booking_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Log successful booking match for AI feedback loop and update staff skills online.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not booking.status or booking.status.lower() != "completed":
        raise HTTPException(status_code=400, detail="Booking must be marked as completed before logging feedback")

    staff = db.query(models.Staff).filter(models.Staff.id == booking.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    complaint_vector = list(booking.complaint_vector) if booking.complaint_vector is not None else None
    if complaint_vector is None and booking.complaint_reason:
        complaint_vector = get_embedding(booking.complaint_reason)
        booking.complaint_vector = complaint_vector

    vector_updated = False
    message = "Feedback logged; staff vector unchanged (no complaint context available)."

    if complaint_vector is not None:
        current_skills_vector = (
            list(staff.skills_vector)
            if staff.skills_vector is not None else complaint_vector
        )

        if len(current_skills_vector) == len(complaint_vector):
            new_vector = [
                (current_value * 0.95) + (complaint_value * 0.05)
                for current_value, complaint_value in zip(current_skills_vector, complaint_vector)
            ]
            staff.skills_vector = new_vector
            vector_updated = True
        else:
            message = "Feedback logged; vector dimensions mismatch prevented an update."

    feedback_log = models.AIFeedbackLog(
        booking_id=booking.id,
        staff_id=staff.id,
        client_complaint_vector=booking.complaint_vector,
        staff_skills_vector=staff.skills_vector
    )

    db.add(feedback_log)
    db.commit()
    db.refresh(feedback_log)
    db.refresh(staff)

    if vector_updated:
        message = "Staff vector updated via online learning."

    return schemas.AIFeedbackLogResponse(
        id=feedback_log.id,
        booking_id=feedback_log.booking_id,
        staff_id=feedback_log.staff_id,
        message=message
    )


# ============================================
# Surgery Endpoints
# ============================================

@app.post("/surgeries/", response_model=schemas.Surgery, tags=["Surgeries"])
def create_surgery(
    surgery: schemas.SurgeryCreate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new surgery. Admin only."""
    db_surgery = models.Surgery(**surgery.model_dump())
    db.add(db_surgery)
    db.commit()
    db.refresh(db_surgery)
    return db_surgery


@app.get("/surgeries/", response_model=List[schemas.Surgery], tags=["Surgeries"])
def get_surgeries(
    date: Optional[date] = None,
    staff_id: Optional[int] = None,
    pet_id: Optional[int] = None,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all surgeries with optional filters. Admin only."""
    query = db.query(models.Surgery)
    
    if date:
        query = query.filter(cast(models.Surgery.start_time, Date) == date)
    if staff_id:
        query = query.filter(models.Surgery.staff_id == staff_id)
    if pet_id:
        query = query.filter(models.Surgery.pet_id == pet_id)
    
    return query.all()


@app.get("/surgeries/{surgery_id}", response_model=schemas.Surgery, tags=["Surgeries"])
def get_surgery(
    surgery_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific surgery by ID. Admin only."""
    surgery = db.query(models.Surgery).filter(models.Surgery.id == surgery_id).first()
    if not surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")
    return surgery


@app.get("/surgeries/check_inventory", response_model=schemas.InventoryCheckResponse, tags=["Surgeries"])
def check_surgery_inventory(
    surgery_type: str,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Check medication inventory for a specific surgery type.
    Returns a list of required medications with their stock status.
    Admin only.
    """
    # Query SurgeryInventoryLink for the given surgery type
    inventory_links = (
        db.query(models.SurgeryInventoryLink)
        .filter(models.SurgeryInventoryLink.surgery_type == surgery_type)
        .all()
    )
    
    if not inventory_links:
        # Return empty list if no inventory links found for this surgery type
        return schemas.InventoryCheckResponse(items=[])
    
    # Build the response items
    items = []
    for link in inventory_links:
        # Get the medication details
        medication = db.query(models.Medication).filter(models.Medication.id == link.medication_id).first()
        
        if medication:
            # Determine status based on stock vs required
            status = "OK" if medication.stock_quantity >= link.required_quantity else "Low"
            
            item = schemas.InventoryCheckItem(
                medication_id=medication.id,
                medication_name=medication.name,
                required_quantity=link.required_quantity,
                stock_quantity=medication.stock_quantity,
                status=status
            )
            items.append(item)
    
    return schemas.InventoryCheckResponse(items=items)


@app.post("/surgeries/{surgery_id}/smart_notes", response_model=schemas.SurgerySmartNotesResponse, tags=["Surgeries"])
async def generate_smart_surgery_notes(
    surgery_id: int,
    smart_notes_request: schemas.SurgerySmartNotesRequest,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Use AI to convert dictated notes into structured surgery notes."""
    surgery = db.query(models.Surgery).filter(models.Surgery.id == surgery_id).first()
    if not surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")

    raw_transcript = smart_notes_request.raw_transcript.strip()
    if not raw_transcript:
        raise HTTPException(status_code=400, detail="raw_transcript cannot be empty")

    prompt = (
        "You are a veterinary scribe. Convert this raw dictation into structured notes "
        "(Vitals, Meds Administered, Observations). Raw text: "
        f"{raw_transcript}."
    )

    try:
        structured_notes = await get_ollama_recommendation(prompt)
    except Exception as exc:  # noqa: BLE001 - surface LLM failures cleanly
        raise HTTPException(status_code=503, detail="Unable to generate smart notes at this time") from exc

    surgery.notes = structured_notes
    db.commit()
    db.refresh(surgery)

    return schemas.SurgerySmartNotesResponse(surgery_id=surgery.id, notes=structured_notes)


@app.put("/surgeries/{surgery_id}", response_model=schemas.Surgery, tags=["Surgeries"])
def update_surgery(
    surgery_id: int,
    surgery_update: schemas.SurgeryUpdate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a surgery. Admin only. Automatically decrements inventory when status is set to 'Completed'."""
    db_surgery = db.query(models.Surgery).filter(models.Surgery.id == surgery_id).first()
    
    if not db_surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")
    
    # Check if status is being changed to "Completed"
    if surgery_update.status and surgery_update.status == "Completed" and db_surgery.status != "Completed":
        # Query SurgeryInventoryLink for required medications
        inventory_links = (
            db.query(models.SurgeryInventoryLink)
            .filter(models.SurgeryInventoryLink.surgery_type == db_surgery.surgery_type)
            .all()
        )
        
        # Decrement stock for each required medication
        for link in inventory_links:
            medication = db.query(models.Medication).filter(models.Medication.id == link.medication_id).first()
            if medication:
                # Decrement stock quantity
                medication.stock_quantity -= link.required_quantity
                # Ensure stock doesn't go negative (optional safety check)
                if medication.stock_quantity < 0:
                    medication.stock_quantity = 0
    
    # Update only the fields that are provided
    update_data = surgery_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_surgery, field, value)
    
    db.commit()
    db.refresh(db_surgery)
    return db_surgery


@app.delete("/surgeries/{surgery_id}", response_model=dict, tags=["Surgeries"])
def delete_surgery(
    surgery_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a surgery. Admin only."""
    db_surgery = db.query(models.Surgery).filter(models.Surgery.id == surgery_id).first()
    
    if not db_surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")
    
    db.delete(db_surgery)
    db.commit()
    return {"ok": True}


@app.get("/admin/inventory/forecast", response_model=List[schemas.InventoryForecastItem], tags=["Medications", "Admin"])
def get_inventory_forecast(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Predict low inventory items based on recent surgery consumption."""
    window_days = 30
    cutoff_date = datetime.utcnow() - timedelta(days=window_days)

    completed_surgeries = (
        db.query(models.Surgery)
        .filter(models.Surgery.start_time >= cutoff_date)
        .filter(models.Surgery.status.isnot(None))
        .filter(func.lower(models.Surgery.status) == "completed")
        .all()
    )

    if not completed_surgeries:
        return []

    links_by_type: Dict[str, List[models.SurgeryInventoryLink]] = defaultdict(list)
    for link in db.query(models.SurgeryInventoryLink).all():
        links_by_type[link.surgery_type].append(link)

    usage_totals: Dict[int, int] = defaultdict(int)
    for surgery in completed_surgeries:
        for link in links_by_type.get(surgery.surgery_type, []):
            usage_totals[link.medication_id] += link.required_quantity

    if not usage_totals:
        return []

    medications = (
        db.query(models.Medication)
        .filter(models.Medication.id.in_(list(usage_totals.keys())))
        .all()
    )

    forecast_items: List[schemas.InventoryForecastItem] = []
    for medication in medications:
        total_used = usage_totals.get(medication.id, 0)
        if total_used <= 0:
            continue

        daily_usage = total_used / window_days
        if daily_usage <= 0:
            continue

        days_remaining = medication.stock_quantity / daily_usage if daily_usage else float("inf")

        if days_remaining < 14:
            forecast_items.append(
                schemas.InventoryForecastItem(
                    medication_name=medication.name,
                    current_stock=medication.stock_quantity,
                    daily_usage=round(daily_usage, 2),
                    days_remaining=round(days_remaining, 1)
                )
            )

    forecast_items.sort(key=lambda item: item.days_remaining)
    return forecast_items


# ============================================
# Medication Endpoints
# ============================================

@app.post("/medications/", response_model=schemas.Medication, tags=["Medications"])
def create_medication(
    medication: schemas.MedicationCreate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new medication. Admin only."""
    db_medication = models.Medication(**medication.model_dump())
    db.add(db_medication)
    db.commit()
    db.refresh(db_medication)
    return db_medication


@app.get("/medications/", response_model=List[schemas.Medication], tags=["Medications"])
def get_medications(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all medications. Admin only."""
    return db.query(models.Medication).all()


@app.get("/medications/{medication_id}", response_model=schemas.Medication, tags=["Medications"])
def get_medication(
    medication_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific medication by ID. Admin only."""
    medication = db.query(models.Medication).filter(models.Medication.id == medication_id).first()
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    return medication


@app.put("/medications/{medication_id}", response_model=schemas.Medication, tags=["Medications"])
def update_medication(
    medication_id: int,
    medication_update: schemas.MedicationUpdate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a medication. Admin only."""
    db_medication = db.query(models.Medication).filter(models.Medication.id == medication_id).first()
    
    if not db_medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    # Update only the fields that are provided
    update_data = medication_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_medication, field, value)
    
    db.commit()
    db.refresh(db_medication)
    return db_medication


@app.delete("/medications/{medication_id}", response_model=dict, tags=["Medications"])
def delete_medication(
    medication_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a medication. Admin only."""
    db_medication = db.query(models.Medication).filter(models.Medication.id == medication_id).first()
    
    if not db_medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    db.delete(db_medication)
    db.commit()
    return {"ok": True}
