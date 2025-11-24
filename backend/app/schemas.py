from typing import List, Optional, Any, Dict
from datetime import datetime, date
from pydantic import BaseModel

# =======================
# Authentication Schemas
# =======================
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenData(BaseModel):
    email: Optional[str] = None

class TokenRefreshRequest(BaseModel):
    refresh_token: str

# =======================
# Base Models
# =======================
class ClientBase(BaseModel):
    name: str
    email: str
    clinic_id: Optional[int] = None

class ClientCreate(ClientBase):
    password: str

class Client(ClientBase):
    id: int
    is_active: bool = True
    class Config:
        orm_mode = True

class StaffBase(BaseModel):
    name: str
    email: str
    role: str
    skills_description: Optional[str] = None

class StaffCreate(StaffBase):
    password: str

class StaffUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    skills_description: Optional[str] = None

class Staff(StaffBase):
    id: int
    class Config:
        orm_mode = True

class PetBase(BaseModel):
    name: str
    species: str
    breed: Optional[str] = None

class PetCreate(PetBase):
    pass

class Pet(PetBase):
    id: int
    client_id: int
    class Config:
        orm_mode = True

# =======================
# Booking Schemas (The Dashboard Fix)
# =======================

# Nested schemas for the Admin Dashboard
class ClientNested(BaseModel):
    id: int
    name: str
    email: str
    class Config:
        orm_mode = True

class PetNested(BaseModel):
    id: int
    name: str
    species: str
    class Config:
        orm_mode = True

class StaffNested(BaseModel):
    id: int
    name: str
    role: str
    class Config:
        orm_mode = True

class BookingBase(BaseModel):
    start_time: datetime
    end_time: datetime
    pet_id: int
    staff_id: int
    complaint_reason: Optional[str] = None

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    staff_id: Optional[int] = None
    complaint_reason: Optional[str] = None

class Booking(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    status: str
    complaint_reason: Optional[str] = None
    client_id: int
    pet_id: int
    staff_id: int
    
    # These nested fields allow the dashboard to show names!
    client: Optional[ClientNested] = None
    pet: Optional[PetNested] = None
    staff: Optional[StaffNested] = None

    class Config:
        orm_mode = True

class BookingByNameCreate(BaseModel):
    pet_name: str
    complaint_reason: Optional[str] = None
    service_type: Optional[str] = None
    preferred_time: datetime

class SuggestedSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    staff_id: int
    staff_name: str
    preference_match: float = 0.0
    reason: str = ""

class ClientRescheduleRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    staff_id: Optional[int] = None

# =======================
# AI & Risk Schemas
# =======================
class RiskAssessment(BaseModel):
    risk_score: float
    risk_level: str
    reasoning: str

class SuggestionRequest(BaseModel):
    complaint_text: str

class SuggestedStaff(BaseModel):
    id: int
    name: str
    role: str

class SuggestionResponse(BaseModel):
    generative_recommendation: str
    suggested_staff: List[SuggestedStaff]

class ChatRequest(BaseModel):
    message: str

class SmartChatRequest(BaseModel):
    prompt: str
    complaint_text: str = ""
    session_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    client_email: Optional[str] = None
    pet_name: Optional[str] = None
    owner_name: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    slots: Optional[List[SuggestedSlot]] = None
    service_type: Optional[str] = None
    ui_action: Optional[str] = None
    suggested_date: Optional[datetime] = None

class AIFeedbackLogResponse(BaseModel):
    id: int
    booking_id: int
    staff_id: int
    message: str

# =======================
# Surgery & Medical Schemas
# =======================
class SurgeryBase(BaseModel):
    surgery_type: str
    start_time: datetime
    end_time: datetime
    pet_id: int
    staff_id: int
    notes: Optional[str] = None
    status: Optional[str] = "Scheduled"

class SurgeryCreate(SurgeryBase):
    pass

class SurgeryUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class Surgery(SurgeryBase):
    id: int
    class Config:
        orm_mode = True

class SurgerySmartNotesRequest(BaseModel):
    raw_transcript: str

class SurgerySmartNotesResponse(BaseModel):
    surgery_id: int
    notes: str

class MedicationBase(BaseModel):
    name: str
    stock_quantity: int
    unit: str

class MedicationCreate(MedicationBase):
    pass

class MedicationUpdate(BaseModel):
    stock_quantity: Optional[int] = None

class Medication(MedicationBase):
    id: int
    class Config:
        orm_mode = True

class InventoryCheckItem(BaseModel):
    medication_id: int
    medication_name: str
    required_quantity: int
    stock_quantity: int
    status: str

class InventoryCheckResponse(BaseModel):
    items: List[InventoryCheckItem]

class InventoryForecastItem(BaseModel):
    medication_name: str
    current_stock: int
    daily_usage: float
    days_remaining: float

# =======================
# Preferences Schemas
# =======================
class PreferencesBase(BaseModel):
    details: str

class PreferencesCreate(PreferencesBase):
    pass

class Preferences(PreferencesBase):
    id: int
    client_id: int
    class Config:
        orm_mode = True

class CancellationSuggestion(BaseModel):
    client_name: str
    client_email: str
    current_booking_id: int
    current_booking_time: datetime
    match_score: float
    reason: str

class CancellationSuggestionResponse(BaseModel):
    cancelled_slot_time: datetime
    suggestions: List[CancellationSuggestion]