from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


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


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


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


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str


class SmartChatRequest(BaseModel):
    prompt: str
    complaint_text: str


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
