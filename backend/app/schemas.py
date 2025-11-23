# backend/app/schemas.py

# Ensure these base schemas exist somewhere above the Booking class
class ClientBase(BaseModel):
    id: int
    name: str
    email: str
    
class PetBase(BaseModel):
    id: int
    name: str
    species: str

class StaffBase(BaseModel):
    id: int
    name: str

# Update the main Booking schema to include nested objects
class Booking(BaseModel):
    id: int
    start_time: datetime
    status: str
    complaint_reason: Optional[str] = None
    
    # The Magic Fix: Include full objects, not just IDs
    client: Optional[ClientBase] = None
    pet: Optional[PetBase] = None
    staff: Optional[StaffBase] = None

    class Config:
        orm_mode = True  # This tells Pydantic to read from the database relationships