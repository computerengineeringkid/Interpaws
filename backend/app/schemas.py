from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr


# Pet Schemas
class PetBase(BaseModel):
    name: str
    species: Optional[str] = None
    breed: Optional[str] = None


class PetCreate(PetBase):
    pass


class Pet(PetBase):
    id: int
    client_id: int

    class Config:
        from_attributes = True


# Client Schemas
class ClientBase(BaseModel):
    name: str
    email: EmailStr
    clinic_id: Optional[int] = None


class ClientCreate(ClientBase):
    password: str


class Client(ClientBase):
    id: int

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Booking Schemas
class BookingBase(BaseModel):
    start_time: datetime
    end_time: datetime
    client_id: int
    pet_id: int
    staff_id: int


class BookingCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    pet_id: int
    staff_id: int


class BookingByNameCreate(BaseModel):
    owner_name: str
    pet_name: str
    service_type: str
    preferred_time: datetime
    complaint_reason: Optional[str] = None


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class ClientRescheduleRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    staff_id: Optional[int] = None


class Booking(BookingBase):
    id: int
    status: str
    complaint_reason: Optional[str] = None

    class Config:
        from_attributes = True


class StaffBase(BaseModel):
    name: str
    role: str


class StaffCreate(StaffBase):
    email: EmailStr
    password: str
    skills_description: Optional[str] = None


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    skills_description: Optional[str] = None


class Staff(StaffBase):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True


class SuggestionRequest(BaseModel):
    complaint_text: str


class SuggestedStaff(BaseModel):
    id: int
    name: str
    role: str

    class Config:
        from_attributes = True


class SuggestionResponse(BaseModel):
    generative_recommendation: str
    suggested_staff: List[SuggestedStaff]


class RiskAssessment(BaseModel):
    risk_score: float  # 0.0 (low) to 1.0 (high)
    risk_level: str    # "Low", "Medium", "High"
    reasoning: str


class SuggestedSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    staff_id: int
    staff_name: Optional[str] = None
    preference_match: Optional[float] = None
    reason: Optional[str] = None


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str
    slots: Optional[List[SuggestedSlot]] = None
    service_type: Optional[str] = None


class SmartChatRequest(BaseModel):
    prompt: str
    complaint_text: str
    session_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    client_email: Optional[str] = None  # For pattern learning
    # Persistent Context Pattern
    pet_name: Optional[str] = None
    owner_name: Optional[str] = None


# Preferences Schemas
class PreferencesBase(BaseModel):
    details: str


class PreferencesCreate(PreferencesBase):
    pass


class Preferences(PreferencesBase):
    id: int
    client_id: int

    class Config:
        from_attributes = True


# AIFeedbackLog Schemas
class AIFeedbackLogBase(BaseModel):
    booking_id: int
    staff_id: int


class AIFeedbackLogCreate(AIFeedbackLogBase):
    pass


class AIFeedbackLog(AIFeedbackLogBase):
    id: int

    class Config:
        from_attributes = True


class AIFeedbackLogResponse(AIFeedbackLog):
    message: str


# Surgery Schemas
class SurgeryBase(BaseModel):
    pet_id: int
    staff_id: int
    surgery_type: str
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    status: str = "Scheduled"


class SurgeryCreate(SurgeryBase):
    pass


class SurgeryUpdate(BaseModel):
    pet_id: Optional[int] = None
    staff_id: Optional[int] = None
    surgery_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class Surgery(SurgeryBase):
    id: int

    class Config:
        from_attributes = True


class SurgerySmartNotesRequest(BaseModel):
    raw_transcript: str


class SurgerySmartNotesResponse(BaseModel):
    surgery_id: int
    notes: str


# Medication Schemas
class MedicationBase(BaseModel):
    name: str
    description: Optional[str] = None
    stock_quantity: int = 0
    unit: str


class MedicationCreate(MedicationBase):
    pass


class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    stock_quantity: Optional[int] = None
    unit: Optional[str] = None


class Medication(MedicationBase):
    id: int

    class Config:
        from_attributes = True


# SurgeryInventoryLink Schemas
class SurgeryInventoryLinkBase(BaseModel):
    surgery_type: str
    medication_id: int
    required_quantity: int = 1


class SurgeryInventoryLinkCreate(SurgeryInventoryLinkBase):
    pass


class SurgeryInventoryLink(SurgeryInventoryLinkBase):
    id: int

    class Config:
        from_attributes = True


# Inventory Check Schemas
class InventoryCheckItem(BaseModel):
    medication_id: int
    medication_name: str
    required_quantity: int
    stock_quantity: int
    status: str  # "OK" or "Low"

    class Config:
        from_attributes = True


class InventoryCheckResponse(BaseModel):
    items: List[InventoryCheckItem]


class InventoryForecastItem(BaseModel):
    medication_name: str
    current_stock: int
    daily_usage: float
    days_remaining: float


# Cancellation Suggestion Schemas (Sprint 8: Dynamic Slot-Filling)
class CancellationSuggestion(BaseModel):
    client_name: str
    client_email: str
    current_booking_id: int
    current_booking_time: datetime
    match_score: float
    reason: str  # e.g., "Prefers morning appointments"

    class Config:
        from_attributes = True


class CancellationSuggestionResponse(BaseModel):
    cancelled_slot_time: datetime
    suggestions: List[CancellationSuggestion]

    class Config:
        from_attributes = True
