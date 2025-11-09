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


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class Booking(BookingBase):
    id: int
    status: str

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
