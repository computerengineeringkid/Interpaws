from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class BookingBase(BaseModel):
    start_time: datetime
    end_time: datetime
    client_id: int
    pet_id: int
    staff_id: int
    complaint_reason: Optional[str] = None


class BookingCreate(BookingBase):
    complaint_reason: Optional[str] = None


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class Booking(BookingBase):
    id: int
    status: str

    class Config:
        from_attributes = True


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


class StaffBase(BaseModel):
    name: str
    role: str


class StaffCreate(StaffBase):
    pass


class Staff(StaffBase):
    id: int

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
