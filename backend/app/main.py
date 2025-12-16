import json
import re
import time
import asyncio
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import Date, cast, text, func, desc
from sqlalchemy.orm import Session

from . import models, schemas
from .schemas import ChatRequest, ChatResponse, SmartChatRequest, Staff, StaffCreate, StaffUpdate, BookingUpdate, StaffChatRequest, StaffChatResponse
from .booking_logic import check_availability
from .database import engine, SessionLocal
from .ai_services import (
    extract_json_payload,
    get_embedding,
    get_ollama_recommendation,
)
from .agent import InterpawsAgent, StaffAgent
from .agent.tools import AgentTools
from .auth import (
    get_password_hash,
    authenticate_client,
    authenticate_staff,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY,
    ALGORITHM
)
from .service_catalog import get_service_duration_minutes, infer_service_type

app = FastAPI()


@app.get("/health")
def healthcheck():
    """Lightweight healthcheck for container orchestration."""
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - surface unhealthy state without failing app startup
        db_status = "unhealthy"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.on_event("startup")
def on_startup() -> None:
    """Ensure DB is reachable and create vector extension with simple retries.

    Also triggers an AI warmup task to load the model into memory immediately.
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

    # --- WARMUP LOGIC ---
    print("🔥 Triggering AI model pre-load in background...")
    # Fire-and-forget the warmup request so the server starts instantly
    # while the model loads in parallel.
    asyncio.create_task(get_ollama_recommendation("warmup"))


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

    repaired = extract_json_payload(raw)
    if repaired:
        return repaired

    # Final defensive catch-all if the repair helper cannot recover data
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _normalize_slots(tool_output: Optional[dict]) -> List[schemas.SuggestedSlot]:
    if not isinstance(tool_output, dict):
        return []

    raw_slots = tool_output.get("slots") or tool_output.get("available_slots")
    if not raw_slots:
        return []

    normalized: List[schemas.SuggestedSlot] = []
    for slot in raw_slots:
        try:
            start_raw = slot.get("start_time")
            end_raw = slot.get("end_time")
            if isinstance(start_raw, str):
                start_time = datetime.fromisoformat(start_raw)
            else:
                start_time = start_raw
            if isinstance(end_raw, str):
                end_time = datetime.fromisoformat(end_raw)
            else:
                end_time = end_raw
            if not start_time or not end_time:
                continue
            normalized.append(
                schemas.SuggestedSlot(
                    start_time=start_time,
                    end_time=end_time,
                    staff_id=slot.get("staff_id") or 0,
                    staff_name=slot.get("staff_name"),
                    preference_match=slot.get("preference_match"),
                    reason=slot.get("reason"),
                )
            )
        except Exception:
            continue

    return normalized


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
    """Login endpoint to get access and refresh tokens."""
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
    refresh_token = create_refresh_token(data={"sub": client.email})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@app.post("/staff/login", response_model=schemas.Token, tags=["Authentication"])
def staff_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Staff login endpoint to get access and refresh tokens for admin users."""
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
    refresh_token = create_refresh_token(data={"sub": staff.email})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@app.post("/refresh", response_model=schemas.Token, tags=["Authentication"])
def refresh_token_endpoint(request: schemas.TokenRefreshRequest):
    """Refresh access token using a valid refresh token."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": request.refresh_token
    }


@app.get("/clients/me", response_model=schemas.Client, tags=["Authentication"])
async def get_current_client(current_user: models.Client = Depends(get_current_user)):
    """Get the currently authenticated client's details."""
    return current_user


@app.get("/clients", tags=["Clients"])
async def get_all_clients(
    search: Optional[str] = Query(None, description="Search by name or email"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of clients (admin only)."""
    query = db.query(models.Client)

    if search:
        query = query.filter(
            (models.Client.name.ilike(f"%{search}%")) |
            (models.Client.email.ilike(f"%{search}%"))
        )

    total = query.count()
    clients = query.offset((page - 1) * per_page).limit(per_page).all()

    # Get pet counts for each client
    result = []
    for client in clients:
        pet_count = db.query(models.Pet).filter(models.Pet.client_id == client.id).count()
        result.append({
            "id": client.id,
            "name": client.name,
            "email": client.email,
            "pet_count": pet_count
        })

    return {
        "clients": result,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


# ============================================
# Booking Endpoints
# ============================================


# ============================================
# Pet Endpoints
# ============================================


@app.get("/pets/me", response_model=List[schemas.Pet], tags=["Pets"])
def get_my_pets(
    name: Optional[str] = Query(None, description="Filter by pet name"),
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # STRICT FILTERING
    query = db.query(models.Pet).filter(models.Pet.client_id == current_user.id)
    if name:
        query = query.filter(models.Pet.name.ilike(f"%{name}%"))
    pets = query.order_by(models.Pet.name.asc()).all()
    return pets


@app.get("/pets/search", tags=["Pets", "Admin"])
def search_pets_by_name_and_owner(
    pet_name: Optional[str] = Query(None, description="Pet name to search"),
    owner_name: Optional[str] = Query(None, description="Owner name to search"),
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Staff endpoint: Search for pets by pet name and/or owner name with detailed info"""
    from sqlalchemy.orm import joinedload
    from datetime import datetime

    query = db.query(models.Pet).options(joinedload(models.Pet.client))

    if pet_name:
        query = query.filter(models.Pet.name.ilike(f"%{pet_name}%"))

    if owner_name:
        query = query.join(models.Client).filter(models.Client.name.ilike(f"%{owner_name}%"))

    pets = query.limit(10).all()

    # Calculate age if date_of_birth exists
    result = []
    for pet in pets:
        pet_dict = {
            "id": pet.id,
            "name": pet.name,
            "species": pet.species,
            "breed": pet.breed,
            "date_of_birth": pet.date_of_birth,
            "client_id": pet.client_id,
            "owner_name": pet.client.name if hasattr(pet, 'client') and pet.client else None,
            "owner_email": pet.client.email if hasattr(pet, 'client') and pet.client else None,
        }

        if pet.date_of_birth:
            age_delta = datetime.now() - pet.date_of_birth
            years = age_delta.days // 365
            months = (age_delta.days % 365) // 30
            pet_dict["age"] = f"{years} years, {months} months"
        else:
            pet_dict["age"] = "Unknown"

        result.append(pet_dict)

    return result


@app.post("/pets", response_model=schemas.Pet, tags=["Pets"])
def create_pet(
    pet: schemas.PetCreate,
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = (
        db.query(models.Pet)
        .filter(
            models.Pet.client_id == current_user.id,
            func.lower(models.Pet.name) == pet.name.lower(),
        )
        .all()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "You already have a pet with that name. Please use a unique name or clarify the pet you want to manage.",
                "pet_ids": [p.id for p in existing],
            },
        )

    db_pet = models.Pet(
        name=pet.name,
        species=pet.species or "Unknown",
        breed=pet.breed or "",
        date_of_birth=pet.date_of_birth,
        client_id=current_user.id,
    )
    db.add(db_pet)
    db.commit()
    db.refresh(db_pet)
    return db_pet

@app.post("/bookings", response_model=schemas.Booking)
async def create_booking(booking: schemas.BookingCreate, current_user: models.Client = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify pet ownership
    pet = db.query(models.Pet).filter(models.Pet.id == booking.pet_id).first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    if pet.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to book for this pet")

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


@app.post("/bookings/by-name", response_model=schemas.Booking, tags=["Bookings"])
async def create_booking_by_name(
    request: schemas.BookingByNameCreate,
    current_user: models.Client = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pets = (
        db.query(models.Pet)
        .filter(models.Pet.client_id == current_user.id, models.Pet.name.ilike(f"%{request.pet_name}%"))
        .all()
    )
    if not pets:
        raise HTTPException(status_code=404, detail="Pet not found for this account")
    if len(pets) > 1:
        raise HTTPException(status_code=400, detail="Multiple pets match that name. Please clarify which pet to book.")

    pet = pets[0]
    service_type, _ = infer_service_type(request.complaint_reason or request.service_type, request.service_type)
    duration_minutes = get_service_duration_minutes(service_type)
    start_time = request.preferred_time
    end_time = start_time + timedelta(minutes=duration_minutes)

    # Check if client already has a booking that overlaps with this time
    existing_bookings = (
        db.query(models.Booking)
        .filter(
            models.Booking.client_id == current_user.id,
            models.Booking.status != "cancelled",
            models.Booking.start_time < end_time,
            models.Booking.end_time > start_time
        )
        .all()
    )

    if existing_bookings:
        existing_time = existing_bookings[0].start_time.strftime("%B %d, %Y at %I:%M %p")
        raise HTTPException(
            status_code=400,
            detail=f"You already have an appointment scheduled at {existing_time}. Please choose a different time slot or cancel your existing appointment first."
        )

    staff_search_text = f"{service_type}: {request.complaint_reason or request.service_type}".strip()
    staff_matches = await AgentTools(db).find_staff(staff_search_text)
    if isinstance(staff_matches, dict):
        raise HTTPException(status_code=400, detail=staff_matches.get("message", "Unable to find staff for that service."))

    chosen_staff = None
    for candidate in staff_matches:
        staff_id = candidate.get("id")
        if staff_id and check_availability(db, staff_id, start_time, end_time):
            chosen_staff = candidate
            break

    if not chosen_staff:
        raise HTTPException(status_code=400, detail="No staff available for that time. Please pick another slot.")

    db_booking = models.Booking(
        start_time=start_time,
        end_time=end_time,
        client_id=current_user.id,
        pet_id=pet.id,
        staff_id=chosen_staff["id"],
        complaint_reason=request.complaint_reason or service_type,
        status="confirmed",
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


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


@app.get("/bookings/{date}", response_model=List[schemas.Booking])
async def get_bookings_for_date(date: date, current_admin: models.Staff = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    return (
        db.query(models.Booking)
        .options(joinedload(models.Booking.client), joinedload(models.Booking.pet), joinedload(models.Booking.staff))
        .filter(cast(models.Booking.start_time, Date) == date)
        .all()
    )


@app.get("/bookings/staff/my-schedule/{date}", response_model=List[schemas.Booking], tags=["Bookings", "Staff"])
async def get_my_staff_schedule(
    date: date,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get bookings for the currently authenticated staff member for a specific date."""
    from sqlalchemy.orm import joinedload
    return (
        db.query(models.Booking)
        .options(joinedload(models.Booking.client), joinedload(models.Booking.pet), joinedload(models.Booking.staff))
        .filter(cast(models.Booking.start_time, Date) == date)
        .filter(models.Booking.staff_id == current_admin.id)
        .order_by(models.Booking.start_time)
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
async def get_reschedule_options(
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
                    slot_embedding = await get_embedding(descriptor)
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
    complaint_vector = await get_embedding(request.complaint_text)
    
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

Be friendly, concise, and professional. Ask the most relevant questions based on the complaint.

IMPORTANT: Do not invent or guess pet names. If the pet's name is not explicitly provided in the context, refer to it only as 'your pet'. Do not use example names like Max or Buddy."""
    
    ai_response = await get_ollama_recommendation(triage_prompt)
    return ChatResponse(response=ai_response)


@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request: SmartChatRequest, db: Session = Depends(get_db)):
    """Smart AI chat endpoint with context from complaint text and staff matching."""
    # Get embedding for the complaint text
    complaint_vector = await get_embedding(request.complaint_text)
    
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

Please answer the user's question using the context provided. Be helpful, friendly, and concise.

IMPORTANT: Do not invent or guess pet names. If the pet's name is not explicitly provided in the context, refer to it only as 'your pet'. Do not use example names like Max or Buddy."""
    
    result_text = await get_ollama_recommendation(enhanced_prompt)
    return ChatResponse(response=result_text)


@app.post("/agent/chat", response_model=ChatResponse, tags=["AI Chat"])
async def agent_chat(request: SmartChatRequest, db: Session = Depends(get_db)):
    """Agentic chat endpoint with Gemini function calling and conversation memory."""
    try:
        # Create agent with client email for context
        agent = InterpawsAgent(db, client_email=request.client_email)

        agent_result = await agent.chat(
            request.prompt,
            session_id=request.session_id,
            prior_history=request.conversation_history,
            client_email=request.client_email,
            complaint_text=request.complaint_text,
            pet_name=request.pet_name,
            owner_name=request.owner_name,
        )

        if isinstance(agent_result, dict):
            # Check for slots in both direct response and tool_output for backward compatibility
            slots = agent_result.get("slots") or _normalize_slots(agent_result.get("tool_output"))
            service_type = agent_result.get("service_type")
            if not service_type:
                tool_output = agent_result.get("tool_output")
                if isinstance(tool_output, dict):
                    service_type = tool_output.get("service_type")
            return ChatResponse(
                response=agent_result.get("response", ""),
                slots=slots or None,
                service_type=service_type,
            )

        return ChatResponse(response=str(agent_result))
    except Exception as e:
        import traceback
        print(f"Agent chat error: {e}")
        traceback.print_exc()
        # Return a user-friendly error message
        error_msg = str(e)
        if "connect" in error_msg.lower() or "connection" in error_msg.lower():
            return ChatResponse(
                response="I'm having trouble connecting to the AI service. Please ensure Ollama is running and try again."
            )
        return ChatResponse(
            response=f"I encountered an error while processing your request. Please try again. (Error: {error_msg})"
        )


@app.post("/agent/chat/enhanced", response_model=ChatResponse, tags=["AI Chat"])
async def enhanced_agent_chat(request: SmartChatRequest, db: Session = Depends(get_db)):
    """
    Enhanced agentic chat endpoint with Gemini function calling.

    Uses Gemini's native function calling for intelligent conversation routing.
    This endpoint now uses the same agentic architecture as /agent/chat.
    """
    try:
        # Use the agentic InterpawsAgent with Gemini function calling
        agent = InterpawsAgent(db, client_email=request.client_email)

        agent_result = await agent.chat(
            request.prompt,
            session_id=request.session_id,
            prior_history=request.conversation_history,
            client_email=request.client_email,
            complaint_text=request.complaint_text,
            pet_name=request.pet_name,
            owner_name=request.owner_name,
        )

        if isinstance(agent_result, dict):
            # Extract slots if present
            slots = agent_result.get("slots")
            if slots and not isinstance(slots, list):
                slots = _normalize_slots({"slots": slots})

            # Get service type if present
            service_type = agent_result.get("service_type")

            return ChatResponse(
                response=agent_result.get("response", ""),
                slots=slots or None,
                service_type=service_type,
            )

        return ChatResponse(response=str(agent_result))
    except Exception as e:
        import traceback
        print(f"Enhanced agent chat error: {e}")
        traceback.print_exc()
        # Return a user-friendly error message
        error_msg = str(e)
        if "connect" in error_msg.lower() or "connection" in error_msg.lower():
            return ChatResponse(
                response="I'm having trouble connecting to the AI service. Please ensure Ollama is running and try again."
            )
        return ChatResponse(
            response=f"I encountered an error while processing your request. Please try again. (Error: {error_msg})"
        )


@app.post("/staff/agent/chat", response_model=StaffChatResponse, tags=["Staff AI"])
async def staff_agent_chat(
    request: StaffChatRequest,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Staff AI Agent endpoint with semantic intent routing.

    Handles staff-specific queries:
    - Schedule management (view appointments, check availability)
    - Patient/client lookup (search pets, view history)
    - Inventory management (check medication stock)
    - Triage assistance (assess symptom urgency)
    - Analytics (booking statistics, trends)
    - Admin booking (book appointments on behalf of clients)
    """
    try:
        agent = StaffAgent(db, current_admin)
        result = await agent.chat(
            request.prompt,
            session_id=request.session_id
        )

        return StaffChatResponse(
            response=result.get("response", ""),
            data=result.get("data"),
            intent=result.get("intent"),
            suggestions=result.get("suggestions")
        )
    except Exception as e:
        import traceback
        print(f"Staff agent chat error: {e}")
        traceback.print_exc()
        return StaffChatResponse(
            response="I encountered an error processing your request. Please try again.",
            intent="error"
        )


# Staff Endpoints
@app.post("/staff", response_model=schemas.Staff, tags=["Staff"])
async def create_staff(staff: schemas.StaffCreate, current_admin: models.Staff = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    """Create a new staff member."""
    # Check if email already exists
    db_staff = db.query(models.Staff).filter(models.Staff.email == staff.email).first()
    if db_staff:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate embedding for skills_description if provided
    skills_vector = None
    if staff.skills_description:
        skills_vector = await get_embedding(staff.skills_description)
    
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


@app.get("/staff", response_model=List[schemas.Staff], tags=["Staff"])
def get_all_staff(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all staff members. Admin only."""
    return db.query(models.Staff).all()


@app.put("/staff/{staff_id}", response_model=schemas.Staff, tags=["Staff"])
async def update_staff(
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
        db_staff.skills_vector = await get_embedding(update_data["skills_description"])
    
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
    earlier_embedding = await get_embedding(f"I prefer earlier appointments, especially {time_description}")
    
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
    details_vector = await get_embedding(preferences.details)
    
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

@app.post("/log-feedback", response_model=schemas.AIFeedbackLogResponse, tags=["AI Feedback"])
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
        complaint_vector = await get_embedding(booking.complaint_reason)
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

@app.post("/surgeries", response_model=schemas.Surgery, tags=["Surgeries"])
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


@app.get("/surgeries", response_model=List[schemas.Surgery], tags=["Surgeries"])
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

@app.post("/medications", response_model=schemas.Medication, tags=["Medications"])
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


@app.get("/medications", response_model=List[schemas.Medication], tags=["Medications"])
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


# ============================================
# Comprehensive Inventory Endpoints
# ============================================

INVENTORY_CATEGORIES = ["medications", "equipment", "supplies", "surgical", "diagnostic", "office"]

@app.get("/inventory/categories", tags=["Inventory"])
def get_inventory_categories(
    current_admin: models.Staff = Depends(get_current_admin_user)
):
    """Get list of valid inventory categories."""
    return {
        "categories": INVENTORY_CATEGORIES,
        "descriptions": {
            "medications": "Pharmaceuticals, vaccines, antibiotics, pain relief",
            "equipment": "Durable medical equipment, monitors, surgical tables",
            "supplies": "Disposable items, bandages, syringes, gloves",
            "surgical": "Surgical instruments, scalpels, forceps, sutures",
            "diagnostic": "Testing supplies, lab equipment, imaging supplies",
            "office": "Administrative supplies, forms, cleaning products"
        }
    }


@app.post("/inventory", response_model=schemas.InventoryItem, tags=["Inventory"])
def create_inventory_item(
    item: schemas.InventoryItemCreate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new inventory item. Admin only."""
    if item.category not in INVENTORY_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(INVENTORY_CATEGORIES)}"
        )

    db_item = models.InventoryItem(
        **item.model_dump(),
        last_restocked=datetime.utcnow() if item.stock_quantity > 0 else None
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/inventory", response_model=List[schemas.InventoryItem], tags=["Inventory"])
def get_inventory_items(
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    low_stock: Optional[bool] = Query(None, description="Filter for low stock items"),
    search: Optional[str] = Query(None, description="Search by name or SKU"),
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all inventory items with optional filters. Admin only."""
    query = db.query(models.InventoryItem).filter(models.InventoryItem.is_active == True)

    if category:
        query = query.filter(models.InventoryItem.category == category)
    if subcategory:
        query = query.filter(models.InventoryItem.subcategory == subcategory)
    if low_stock:
        query = query.filter(models.InventoryItem.stock_quantity <= models.InventoryItem.min_stock_level)
    if search:
        query = query.filter(
            (models.InventoryItem.name.ilike(f"%{search}%")) |
            (models.InventoryItem.sku.ilike(f"%{search}%"))
        )

    return query.order_by(models.InventoryItem.category, models.InventoryItem.name).all()


@app.get("/inventory/summary", response_model=schemas.InventorySummary, tags=["Inventory"])
def get_inventory_summary(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get inventory summary with category breakdown. Admin only."""
    items = db.query(models.InventoryItem).filter(models.InventoryItem.is_active == True).all()

    total_items = len(items)
    total_value = sum((item.unit_cost or 0) * item.stock_quantity for item in items)
    low_stock_items = sum(1 for item in items if item.stock_quantity <= item.min_stock_level and item.stock_quantity > 0)
    out_of_stock_items = sum(1 for item in items if item.stock_quantity == 0)

    # Count items expiring within 30 days
    expiry_cutoff = datetime.utcnow() + timedelta(days=30)
    expiring_soon = sum(1 for item in items if item.expiration_date and item.expiration_date <= expiry_cutoff)

    # Category breakdown
    category_stats = {}
    for item in items:
        if item.category not in category_stats:
            category_stats[item.category] = {
                "category": item.category,
                "total_items": 0,
                "low_stock_count": 0,
                "out_of_stock_count": 0,
                "total_value": 0
            }

        stats = category_stats[item.category]
        stats["total_items"] += 1
        stats["total_value"] += (item.unit_cost or 0) * item.stock_quantity
        if item.stock_quantity == 0:
            stats["out_of_stock_count"] += 1
        elif item.stock_quantity <= item.min_stock_level:
            stats["low_stock_count"] += 1

    return schemas.InventorySummary(
        total_items=total_items,
        total_value=total_value,
        low_stock_items=low_stock_items,
        out_of_stock_items=out_of_stock_items,
        expiring_soon=expiring_soon,
        category_breakdown=[
            schemas.InventoryCategoryStats(**stats)
            for stats in category_stats.values()
        ]
    )


@app.get("/inventory/{item_id}", response_model=schemas.InventoryItem, tags=["Inventory"])
def get_inventory_item(
    item_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific inventory item by ID. Admin only."""
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@app.put("/inventory/{item_id}", response_model=schemas.InventoryItem, tags=["Inventory"])
def update_inventory_item(
    item_id: int,
    item_update: schemas.InventoryItemUpdate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update an inventory item. Admin only."""
    db_item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()

    if not db_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    update_data = item_update.model_dump(exclude_unset=True)

    # Validate category if being updated
    if "category" in update_data and update_data["category"] not in INVENTORY_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(INVENTORY_CATEGORIES)}"
        )

    # Track restocking
    if "stock_quantity" in update_data:
        new_qty = update_data["stock_quantity"]
        if new_qty > db_item.stock_quantity:
            db_item.last_restocked = datetime.utcnow()

    for field, value in update_data.items():
        setattr(db_item, field, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@app.post("/inventory/{item_id}/adjust", response_model=schemas.InventoryItem, tags=["Inventory"])
def adjust_inventory_stock(
    item_id: int,
    adjustment: schemas.InventoryStockAdjustment,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Adjust stock quantity for an inventory item. Admin only."""
    db_item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()

    if not db_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    new_quantity = db_item.stock_quantity + adjustment.quantity_change
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Stock cannot go below zero")

    db_item.stock_quantity = new_quantity
    if adjustment.quantity_change > 0:
        db_item.last_restocked = datetime.utcnow()

    db.commit()
    db.refresh(db_item)
    return db_item


@app.delete("/inventory/{item_id}", response_model=dict, tags=["Inventory"])
def delete_inventory_item(
    item_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Soft delete an inventory item. Admin only."""
    db_item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()

    if not db_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    db_item.is_active = False
    db.commit()
    return {"ok": True}


# ============================================
# Client Analytics Endpoints
# ============================================

@app.get("/admin/analytics/clients/no-show-risk", response_model=schemas.NoShowRiskReport, tags=["Analytics", "Admin"])
def get_no_show_risk_report(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get no-show risk report for all clients. Admin only."""
    clients = db.query(models.Client).all()

    high_risk = []
    medium_risk = []
    total_no_shows = 0
    total_appointments = 0

    for client in clients:
        # Get analytics for this client
        analytics = db.query(models.ClientAnalytics).filter(
            models.ClientAnalytics.client_id == client.id
        ).first()

        # Count appointments
        bookings = db.query(models.Booking).filter(
            models.Booking.client_id == client.id
        ).all()

        completed = sum(1 for b in bookings if b.status == "completed")
        cancelled = sum(1 for b in bookings if b.status == "cancelled")
        no_shows = sum(1 for b in bookings if b.status == "no_show")
        total = len(bookings)

        total_appointments += total
        total_no_shows += no_shows

        # Calculate rates
        no_show_rate = (no_shows / total) if total > 0 else 0
        cancellation_rate = (cancelled / total) if total > 0 else 0
        completion_rate = (completed / total) if total > 0 else 0

        # Determine risk level
        if no_show_rate >= 0.3 or (no_show_rate >= 0.2 and cancellation_rate >= 0.3):
            risk_level = "high"
        elif no_show_rate >= 0.15 or cancellation_rate >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        pets_count = db.query(models.Pet).filter(models.Pet.client_id == client.id).count()

        client_data = schemas.ClientWithAnalytics(
            id=client.id,
            name=client.name,
            email=client.email,
            pets_count=pets_count,
            analytics=schemas.ClientAnalytics(
                id=analytics.id if analytics else 0,
                client_id=client.id,
                total_appointments=total,
                completed_appointments=completed,
                cancelled_appointments=cancelled,
                no_show_count=no_shows,
                no_show_rate=round(no_show_rate, 3),
                cancellation_rate=round(cancellation_rate, 3),
                completion_rate=round(completion_rate, 3),
                risk_level=risk_level
            ) if total > 0 else None
        )

        if risk_level == "high":
            high_risk.append(client_data)
        elif risk_level == "medium":
            medium_risk.append(client_data)

    overall_no_show_rate = (total_no_shows / total_appointments) if total_appointments > 0 else 0

    return schemas.NoShowRiskReport(
        high_risk_clients=sorted(high_risk, key=lambda x: x.analytics.no_show_rate if x.analytics else 0, reverse=True),
        medium_risk_clients=sorted(medium_risk, key=lambda x: x.analytics.no_show_rate if x.analytics else 0, reverse=True),
        total_high_risk=len(high_risk),
        total_medium_risk=len(medium_risk),
        overall_no_show_rate=round(overall_no_show_rate, 3)
    )


@app.get("/admin/analytics/clients/engagement", response_model=schemas.ClientEngagementStats, tags=["Analytics", "Admin"])
def get_client_engagement_stats(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get client engagement statistics. Admin only."""
    now = datetime.utcnow()
    ninety_days_ago = now - timedelta(days=90)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    clients = db.query(models.Client).all()

    active_clients = 0
    inactive_clients = 0
    new_clients_this_month = 0
    returning_clients_this_month = 0
    total_visits = 0
    client_visit_data = []

    for client in clients:
        bookings = db.query(models.Booking).filter(
            models.Booking.client_id == client.id,
            models.Booking.status.in_(["completed", "confirmed"])
        ).order_by(models.Booking.start_time.desc()).all()

        visit_count = len(bookings)
        total_visits += visit_count

        # Check if active (visited in last 90 days)
        last_visit = bookings[0].start_time if bookings else None
        if last_visit and last_visit >= ninety_days_ago:
            active_clients += 1
        else:
            inactive_clients += 1

        # Check for first visit this month
        first_booking = db.query(models.Booking).filter(
            models.Booking.client_id == client.id
        ).order_by(models.Booking.start_time.asc()).first()

        if first_booking and first_booking.start_time >= month_start:
            new_clients_this_month += 1
        elif bookings and any(b.start_time >= month_start for b in bookings):
            returning_clients_this_month += 1

        pets_count = db.query(models.Pet).filter(models.Pet.client_id == client.id).count()

        client_visit_data.append({
            "client": client,
            "visit_count": visit_count,
            "pets_count": pets_count,
            "last_visit": last_visit
        })

    # Calculate averages
    total_clients = len(clients)
    average_visits_per_client = (total_visits / total_clients) if total_clients > 0 else 0

    # Get top clients by visit count
    top_client_data = sorted(client_visit_data, key=lambda x: x["visit_count"], reverse=True)[:10]
    top_clients = [
        schemas.ClientWithAnalytics(
            id=data["client"].id,
            name=data["client"].name,
            email=data["client"].email,
            pets_count=data["pets_count"],
            analytics=schemas.ClientAnalytics(
                id=0,
                client_id=data["client"].id,
                total_appointments=data["visit_count"],
                completed_appointments=data["visit_count"],
                cancelled_appointments=0,
                no_show_count=0,
                last_visit_date=data["last_visit"]
            ) if data["visit_count"] > 0 else None
        )
        for data in top_client_data
    ]

    return schemas.ClientEngagementStats(
        active_clients=active_clients,
        inactive_clients=inactive_clients,
        new_clients_this_month=new_clients_this_month,
        returning_clients_this_month=returning_clients_this_month,
        average_visits_per_client=round(average_visits_per_client, 2),
        top_clients=top_clients
    )


@app.get("/admin/analytics/clients/{client_id}", tags=["Analytics", "Admin"])
def get_client_analytics(
    client_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed analytics for a specific client. Admin only."""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    bookings = db.query(models.Booking).filter(
        models.Booking.client_id == client_id
    ).order_by(models.Booking.start_time.desc()).all()

    completed = sum(1 for b in bookings if b.status == "completed")
    cancelled = sum(1 for b in bookings if b.status == "cancelled")
    no_shows = sum(1 for b in bookings if b.status == "no_show")
    confirmed = sum(1 for b in bookings if b.status == "confirmed")
    total = len(bookings)

    pets = db.query(models.Pet).filter(models.Pet.client_id == client_id).all()

    # Get booking history with details
    booking_history = []
    for booking in bookings[:20]:  # Last 20 bookings
        pet = next((p for p in pets if p.id == booking.pet_id), None)
        staff = db.query(models.Staff).filter(models.Staff.id == booking.staff_id).first()
        booking_history.append({
            "id": booking.id,
            "date": booking.start_time.isoformat(),
            "status": booking.status,
            "pet_name": pet.name if pet else "Unknown",
            "staff_name": staff.name if staff else "Unknown",
            "reason": booking.complaint_reason
        })

    # Calculate rates
    no_show_rate = (no_shows / total) if total > 0 else 0
    cancellation_rate = (cancelled / total) if total > 0 else 0
    completion_rate = (completed / total) if total > 0 else 0

    # Determine risk level
    if no_show_rate >= 0.3 or (no_show_rate >= 0.2 and cancellation_rate >= 0.3):
        risk_level = "high"
    elif no_show_rate >= 0.15 or cancellation_rate >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "client": {
            "id": client.id,
            "name": client.name,
            "email": client.email
        },
        "pets": [{"id": p.id, "name": p.name, "species": p.species, "breed": p.breed} for p in pets],
        "statistics": {
            "total_appointments": total,
            "completed": completed,
            "cancelled": cancelled,
            "no_shows": no_shows,
            "upcoming": confirmed,
            "no_show_rate": round(no_show_rate * 100, 1),
            "cancellation_rate": round(cancellation_rate * 100, 1),
            "completion_rate": round(completion_rate * 100, 1),
            "risk_level": risk_level
        },
        "recent_bookings": booking_history,
        "first_visit": bookings[-1].start_time.isoformat() if bookings else None,
        "last_visit": bookings[0].start_time.isoformat() if bookings else None
    }


@app.put("/bookings/{booking_id}/mark-no-show", response_model=schemas.Booking, tags=["Bookings", "Admin"])
def mark_booking_no_show(
    booking_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Mark a booking as no-show. Admin only."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot mark cancelled booking as no-show")

    booking.status = "no_show"
    db.commit()
    db.refresh(booking)

    # Update client analytics if exists
    analytics = db.query(models.ClientAnalytics).filter(
        models.ClientAnalytics.client_id == booking.client_id
    ).first()

    if analytics:
        analytics.no_show_count += 1
        db.commit()

    return booking


# ============================================
# Service & Pricing Endpoints
# ============================================

SERVICE_CATEGORIES = ["checkup", "vaccination", "surgery", "dental", "grooming", "emergency", "diagnostic", "wellness"]

@app.post("/services", response_model=schemas.Service, tags=["Services"])
def create_service(
    service: schemas.ServiceCreate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new service. Admin only."""
    db_service = models.Service(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service


@app.get("/services", response_model=List[schemas.Service], tags=["Services"])
def get_services(
    category: Optional[str] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only show active services"),
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all services. Admin only."""
    query = db.query(models.Service)
    if active_only:
        query = query.filter(models.Service.is_active == True)
    if category:
        query = query.filter(models.Service.category == category)
    return query.order_by(models.Service.category, models.Service.name).all()


@app.get("/services/{service_id}", response_model=schemas.Service, tags=["Services"])
def get_service(
    service_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific service. Admin only."""
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@app.put("/services/{service_id}", response_model=schemas.Service, tags=["Services"])
def update_service(
    service_id: int,
    service_update: schemas.ServiceUpdate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a service. Admin only."""
    db_service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = service_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_service, field, value)

    db.commit()
    db.refresh(db_service)
    return db_service


@app.delete("/services/{service_id}", response_model=dict, tags=["Services"])
def delete_service(
    service_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Soft delete a service. Admin only."""
    db_service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")

    db_service.is_active = False
    db.commit()
    return {"ok": True}


@app.get("/admin/analytics/revenue", response_model=schemas.RevenueStats, tags=["Analytics", "Admin"])
def get_revenue_stats(
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get revenue statistics. Admin only."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        last_month_start = month_start.replace(year=now.year - 1, month=12)
    else:
        last_month_start = month_start.replace(month=now.month - 1)

    # Get all bookings with prices
    bookings = db.query(models.Booking).filter(
        models.Booking.price.isnot(None),
        models.Booking.status.in_(["completed", "confirmed"])
    ).all()

    total_revenue = sum(b.price or 0 for b in bookings)
    revenue_this_month = sum(b.price or 0 for b in bookings if b.start_time >= month_start)
    revenue_last_month = sum(
        b.price or 0 for b in bookings
        if b.start_time >= last_month_start and b.start_time < month_start
    )

    bookings_with_price = [b for b in bookings if b.price]
    average_booking_value = (total_revenue // len(bookings_with_price)) if bookings_with_price else 0

    # Top services by revenue
    service_revenue = {}
    for booking in bookings:
        if booking.service_id and booking.price:
            service = db.query(models.Service).filter(models.Service.id == booking.service_id).first()
            if service:
                if service.name not in service_revenue:
                    service_revenue[service.name] = {"name": service.name, "revenue": 0, "count": 0}
                service_revenue[service.name]["revenue"] += booking.price
                service_revenue[service.name]["count"] += 1

    top_services = sorted(service_revenue.values(), key=lambda x: x["revenue"], reverse=True)[:5]

    # Revenue by category
    category_revenue = {}
    for booking in bookings:
        if booking.service_id and booking.price:
            service = db.query(models.Service).filter(models.Service.id == booking.service_id).first()
            if service and service.category:
                category_revenue[service.category] = category_revenue.get(service.category, 0) + booking.price

    return schemas.RevenueStats(
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        revenue_last_month=revenue_last_month,
        average_booking_value=average_booking_value,
        top_services=top_services,
        revenue_by_category=category_revenue
    )


# ============================================
# Email Campaign Endpoints
# ============================================

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@interpaws.com")


@app.post("/email/campaigns", response_model=schemas.EmailCampaign, tags=["Email"])
def create_email_campaign(
    campaign: schemas.EmailCampaignCreate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new email campaign. Admin only."""
    db_campaign = models.EmailCampaign(
        **campaign.model_dump(),
        created_by=current_admin.id,
        created_at=datetime.utcnow(),
        status="draft"
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@app.get("/email/campaigns", response_model=List[schemas.EmailCampaign], tags=["Email"])
def get_email_campaigns(
    status: Optional[str] = Query(None, description="Filter by status"),
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all email campaigns. Admin only."""
    query = db.query(models.EmailCampaign)
    if status:
        query = query.filter(models.EmailCampaign.status == status)
    return query.order_by(desc(models.EmailCampaign.created_at)).all()


@app.get("/email/campaigns/{campaign_id}", response_model=schemas.EmailCampaign, tags=["Email"])
def get_email_campaign(
    campaign_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific email campaign. Admin only."""
    campaign = db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@app.put("/email/campaigns/{campaign_id}", response_model=schemas.EmailCampaign, tags=["Email"])
def update_email_campaign(
    campaign_id: int,
    campaign_update: schemas.EmailCampaignUpdate,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update an email campaign. Admin only."""
    db_campaign = db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign_id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = campaign_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_campaign, field, value)

    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@app.delete("/email/campaigns/{campaign_id}", response_model=dict, tags=["Email"])
def delete_email_campaign(
    campaign_id: int,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete an email campaign. Admin only."""
    db_campaign = db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign_id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    db.delete(db_campaign)
    db.commit()
    return {"ok": True}


@app.post("/email/generate", response_model=schemas.EmailGenerateResponse, tags=["Email", "AI"])
async def generate_email_content(
    request: schemas.EmailGenerateRequest,
    current_admin: models.Staff = Depends(get_current_admin_user)
):
    """Generate email content using AI. Admin only."""
    campaign_prompts = {
        "reminder": "appointment reminder for an upcoming vet visit",
        "promotion": "promotional offer for clinic services",
        "follow_up": "follow-up after a recent visit to check on pet health",
        "vaccination_due": "reminder that vaccinations are due soon",
        "checkup_reminder": "annual or semi-annual wellness checkup reminder"
    }

    campaign_desc = campaign_prompts.get(request.campaign_type, "general veterinary clinic communication")

    prompt = f"""Generate a {request.tone} email for a veterinary clinic.

Purpose: {campaign_desc}

Additional context: {request.context or 'None provided'}
Client name: {request.client_name or '[Client Name]'}
Pet name: {request.pet_name or '[Pet Name]'}

Generate a professional email with:
1. A compelling subject line
2. A friendly opening
3. The main message
4. A clear call to action
5. A warm closing

Respond in JSON format:
{{"subject": "subject line here", "body": "full email body here"}}

Use placeholders like [Client Name], [Pet Name], [Date], [Time] where specific info is needed.
Keep the email concise and friendly. Include the clinic name "Interpaws Veterinary Clinic" in the signature."""

    try:
        llm_response = await get_ollama_recommendation(prompt)
        result = _extract_json_payload(llm_response)
        if result and "subject" in result and "body" in result:
            return schemas.EmailGenerateResponse(
                subject=result["subject"],
                body=result["body"]
            )
    except Exception as e:
        print(f"Error generating email: {e}")

    # Fallback templates
    templates = {
        "reminder": {
            "subject": "Reminder: Upcoming Appointment at Interpaws",
            "body": f"""Dear {request.client_name or '[Client Name]'},

This is a friendly reminder about your upcoming appointment for {request.pet_name or '[Pet Name]'} at Interpaws Veterinary Clinic.

Please arrive 10 minutes early to complete any necessary paperwork. If you need to reschedule, please contact us at least 24 hours in advance.

We look forward to seeing you and {request.pet_name or '[Pet Name]'} soon!

Best regards,
The Interpaws Team"""
        },
        "vaccination_due": {
            "subject": f"Vaccination Due for {request.pet_name or 'Your Pet'}",
            "body": f"""Dear {request.client_name or '[Client Name]'},

Our records indicate that {request.pet_name or '[Pet Name]'}'s vaccinations are coming due. Keeping vaccines up to date is essential for your pet's health and well-being.

Please schedule an appointment at your earliest convenience to ensure {request.pet_name or '[Pet Name]'} stays protected.

To book online or call us at (555) 123-4567.

Warm regards,
The Interpaws Veterinary Team"""
        }
    }

    template = templates.get(request.campaign_type, {
        "subject": "A Message from Interpaws Veterinary Clinic",
        "body": f"""Dear {request.client_name or '[Client Name]'},

Thank you for choosing Interpaws Veterinary Clinic for {request.pet_name or '[Pet Name]'}'s care.

{request.context or 'We wanted to reach out to ensure your pet is healthy and happy.'}

Please don't hesitate to contact us if you have any questions.

Best regards,
The Interpaws Team"""
    })

    return schemas.EmailGenerateResponse(**template)


@app.post("/email/send", response_model=schemas.SendEmailResponse, tags=["Email"])
async def send_email(
    request: schemas.SendEmailRequest,
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Send an email via SendGrid. Admin only."""
    if not SENDGRID_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="SendGrid is not configured. Please set SENDGRID_API_KEY in environment variables."
        )

    # Create email send record
    db_send = models.EmailSend(
        campaign_id=request.campaign_id,
        client_id=request.client_id,
        email_address=request.to_email,
        status="pending"
    )
    db.add(db_send)
    db.commit()
    db.refresh(db_send)

    try:
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=request.to_email,
            subject=request.subject,
            html_content=request.body.replace('\n', '<br>')
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in [200, 201, 202]:
            db_send.status = "sent"
            db_send.sent_at = datetime.utcnow()
            db.commit()

            return schemas.SendEmailResponse(
                success=True,
                message=f"Email sent successfully to {request.to_email}",
                email_send_id=db_send.id
            )
        else:
            db_send.status = "failed"
            db.commit()
            raise HTTPException(status_code=500, detail=f"SendGrid error: {response.status_code}")

    except Exception as e:
        db_send.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@app.post("/email/send-test", response_model=schemas.SendEmailResponse, tags=["Email"])
async def send_test_email(
    to_email: str = Query(..., description="Email address to send test to"),
    campaign_id: int = Query(..., description="Campaign ID to test"),
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Send a test email for a campaign. Admin only."""
    campaign = db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return await send_email(
        schemas.SendEmailRequest(
            to_email=to_email,
            subject=f"[TEST] {campaign.subject}",
            body=campaign.body,
            campaign_id=campaign.id
        ),
        current_admin=current_admin,
        db=db
    )


@app.get("/email/sends", response_model=List[schemas.EmailSend], tags=["Email"])
def get_email_sends(
    campaign_id: Optional[int] = Query(None, description="Filter by campaign"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_admin: models.Staff = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get email send history. Admin only."""
    query = db.query(models.EmailSend)
    if campaign_id:
        query = query.filter(models.EmailSend.campaign_id == campaign_id)
    if status:
        query = query.filter(models.EmailSend.status == status)
    return query.order_by(desc(models.EmailSend.sent_at)).limit(100).all()
