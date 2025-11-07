from datetime import datetime
from typing import List
from pydantic import BaseModel


class BookingBase(BaseModel):
    start_time: datetime
    end_time: datetime
    client_id: int
    pet_id: int
    staff_id: int


class BookingCreate(BookingBase):
    pass


class Booking(BookingBase):
    id: int
    status: str

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
