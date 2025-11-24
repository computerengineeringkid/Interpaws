from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .database import Base  # Import the Base from database.py

class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, index=True) # e.g., "Veterinarian", "Technician"
    skills_description = Column(Text, nullable=True)
    skills_vector = Column(Vector(384), nullable=True)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    clinic_id = Column(Integer, ForeignKey("clinics.id"))


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    species = Column(String, index=True)
    breed = Column(String)
    date_of_birth = Column(DateTime, nullable=True)
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
    complaint_reason = Column(Text, nullable=True)
    complaint_vector = Column(Vector(384), nullable=True)

    # Relationships for eager loading
    client = relationship("Client", foreign_keys=[client_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
    staff = relationship("Staff", foreign_keys=[staff_id])


class Preferences(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    details = Column(Text)
    client_id = Column(Integer, ForeignKey("clients.id"))
    details_vector = Column(Vector(384), nullable=True)


class AIFeedbackLog(Base):
    __tablename__ = "ai_feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"))
    client_complaint_vector = Column(Vector(384), nullable=True)
    staff_skills_vector = Column(Vector(384), nullable=True)


class Surgery(Base):
    __tablename__ = "surgeries"

    id = Column(Integer, primary_key=True, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"))
    staff_id = Column(Integer, ForeignKey("staff.id"))  # Primary surgeon
    surgery_type = Column(String)  # e.g., "Spay", "Orthopedic"
    notes = Column(Text, nullable=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, index=True)  # e.g., "Scheduled", "In-Progress", "Completed"


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    stock_quantity = Column(Integer, default=0)
    unit = Column(String)  # e.g., "mg", "ml", "tablets"


class SurgeryInventoryLink(Base):
    __tablename__ = "surgery_inventory_links"

    id = Column(Integer, primary_key=True, index=True)
    surgery_type = Column(String, index=True)  # e.g., "Spay", "Orthopedic"
    medication_id = Column(Integer, ForeignKey("medications.id"))
    required_quantity = Column(Integer, default=1)
