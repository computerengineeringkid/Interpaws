from datetime import datetime
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
