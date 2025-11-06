from sqlalchemy import Column, Integer, String
from .database import Base  # Import the Base from database.py

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String, index=True) # e.g., "Veterinarian", "Technician"
