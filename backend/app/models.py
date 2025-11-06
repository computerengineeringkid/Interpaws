from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
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


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"))


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    species = Column(String, index=True)
    breed = Column(String)
    client_id = Column(Integer, ForeignKey("clients.id"))


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)
    status = Column(String, default='confirmed', index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    pet_id = Column(Integer, ForeignKey("pets.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"))


class Preferences(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    details = Column(Text)
    client_id = Column(Integer, ForeignKey("clients.id"))
